from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import get_scope_user_ids
from app.models.access_control import UserSupervisorAccess
from app.models.all_models import Inspection, InspectionStatus, MediaType, RoleCode, Station, User, UserStationAccess

router = APIRouter()

SUBMITTED_WEEKLY_STATUSES = {
    InspectionStatus.UNDER_LINE_MANAGER_REVIEW,
    InspectionStatus.LINE_MANAGER_RECOMMENDED,
    InspectionStatus.DGM_APPROVED,
    InspectionStatus.DGM_REJECTED,
    InspectionStatus.GM_REVIEW_REQUIRED,
    InspectionStatus.GM_REVIEWED,
    InspectionStatus.CLOSED,
}

WEEKLY_TARGETS: dict[RoleCode, dict[str, Any]] = {
    RoleCode.STATION_MANAGER: {
        "required": 3,
        "role_label": "SM",
        "label": "Station Manager weekly inspection target",
    },
    RoleCode.EIT_MEMBER: {
        "required": 1,
        "role_label": "EIT",
        "label": "EIT weekly inspection target",
    },
}

LM_ROLES = {RoleCode.AM_MGR_LINE, RoleCode.AM_MGR_HK}
DGM_ROLES = {RoleCode.DGM_LINE, RoleCode.DGM_HK}
GM_ROLES = {RoleCode.GM_OPS}


def _role_value(user: User) -> str | None:
    return user.role.code.value if user and user.role else None


def _role_code(user: User) -> RoleCode | None:
    return user.role.code if user and user.role else None


def _role_label(code: RoleCode | str | None) -> str:
    value = code.value if hasattr(code, "value") else str(code or "")
    labels = {
        "SUPER_ADMIN": "Super Admin",
        "HK_CELL_ADMIN": "HK Cell Admin",
        "GM_OPS": "GM/Ops",
        "DGM_LINE": "DGM Line",
        "DGM_HK": "DGM HK",
        "AM_MGR_LINE": "Line Manager",
        "AM_MGR_HK": "HK Manager",
        "STATION_MANAGER": "Station Manager",
        "EIT_MEMBER": "External Inspection Team",
        "AUDITOR": "Auditor",
    }
    return labels.get(value, value or "-")


def _current_week_window(today: date | None = None) -> tuple[date, date]:
    current = today or date.today()
    week_start = current - timedelta(days=current.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _visible_inspectors(db: Session, actor: User) -> list[User]:
    scope_ids = get_scope_user_ids(db, actor, include_self=True)
    query = db.query(User).options(joinedload(User.role)).filter(User.is_active.is_(True))
    if scope_ids is not None:
        if not scope_ids:
            return []
        query = query.filter(User.id.in_(scope_ids))

    users = query.order_by(User.name.asc()).all()
    return [u for u in users if _role_code(u) in WEEKLY_TARGETS]


def _station_map_for_users(db: Session, user_ids: list[int]) -> dict[int, list[Station]]:
    if not user_ids:
        return {}

    rows = (
        db.query(UserStationAccess, Station)
        .join(Station, Station.id == UserStationAccess.station_id)
        .filter(
            UserStationAccess.user_id.in_(user_ids),
            UserStationAccess.is_active.is_(True),
            Station.is_active.is_(True),
        )
        .order_by(Station.station_name.asc())
        .all()
    )
    result: dict[int, list[Station]] = {}
    seen: set[tuple[int, int]] = set()
    for access, station in rows:
        key = (access.user_id, station.id)
        if key in seen:
            continue
        seen.add(key)
        result.setdefault(access.user_id, []).append(station)
    return result


def _weekly_counts(db: Session, user_ids: list[int], week_start: date, week_end: date) -> dict[tuple[int, int], int]:
    if not user_ids:
        return {}

    rows = (
        db.query(Inspection.submitted_by, Inspection.station_id, func.count(Inspection.id))
        .filter(
            Inspection.submitted_by.in_(user_ids),
            Inspection.inspection_date >= week_start,
            Inspection.inspection_date <= week_end,
            Inspection.status.in_(SUBMITTED_WEEKLY_STATUSES),
        )
        .group_by(Inspection.submitted_by, Inspection.station_id)
        .all()
    )
    return {(int(user_id), int(station_id)): int(count or 0) for user_id, station_id, count in rows}


def _parent_maps(db: Session, users_by_id: dict[int, User]) -> dict[int, list[User]]:
    links = (
        db.query(UserSupervisorAccess)
        .filter(UserSupervisorAccess.is_active.is_(True))
        .all()
    )
    parents: dict[int, list[User]] = {}
    for link in links:
        supervisor = users_by_id.get(int(link.supervisor_user_id))
        subordinate = users_by_id.get(int(link.subordinate_user_id))
        if not supervisor or not subordinate or not supervisor.is_active or not subordinate.is_active:
            continue
        parents.setdefault(int(link.subordinate_user_id), []).append(supervisor)
    return parents


def _supervisor_names_for(user: User, parents: dict[int, list[User]]) -> dict[str, str | None]:
    chain = {"line_manager": [], "dgm": [], "gm": []}
    frontier = [int(user.id)]
    visited: set[int] = set()

    for _ in range(6):
        next_frontier: list[int] = []
        for current_id in frontier:
            for parent in parents.get(current_id, []):
                parent_id = int(parent.id)
                if parent_id in visited:
                    continue
                visited.add(parent_id)
                code = _role_code(parent)
                label = f"{parent.name} ({_role_label(code)})"
                if code in LM_ROLES:
                    chain["line_manager"].append(label)
                elif code in DGM_ROLES:
                    chain["dgm"].append(label)
                elif code in GM_ROLES:
                    chain["gm"].append(label)
                next_frontier.append(parent_id)
        if not next_frontier:
            break
        frontier = next_frontier

    return {
        "line_manager": ", ".join(chain["line_manager"]) or None,
        "dgm": ", ".join(chain["dgm"]) or None,
        "gm": ", ".join(chain["gm"]) or None,
    }


def _build_weekly_report(db: Session, actor: User, only_pending: bool = False) -> dict[str, Any]:
    week_start, week_end = _current_week_window()
    inspectors = _visible_inspectors(db, actor)
    inspector_ids = [int(user.id) for user in inspectors]

    # Include all active users in user lookup so supervisor chain names resolve even when the
    # actor sees only a subtree of inspectors.
    all_users = db.query(User).options(joinedload(User.role)).filter(User.is_active.is_(True)).all()
    users_by_id = {int(user.id): user for user in all_users}
    parents = _parent_maps(db, users_by_id)

    station_map = _station_map_for_users(db, inspector_ids)
    counts = _weekly_counts(db, inspector_ids, week_start, week_end)

    rows: list[dict[str, Any]] = []
    unique_station_ids: set[int] = set()

    for inspector in inspectors:
        role_code = _role_code(inspector)
        target = WEEKLY_TARGETS.get(role_code)
        if not target:
            continue
        required = int(target["required"])
        stations = station_map.get(int(inspector.id), [])
        supervisors = _supervisor_names_for(inspector, parents)

        if not stations:
            rows.append(
                {
                    "inspector_id": inspector.id,
                    "inspector_name": inspector.name,
                    "emp_number": inspector.emp_number,
                    "username": inspector.username,
                    "role": _role_value(inspector),
                    "role_label": target["role_label"],
                    "station_id": None,
                    "station_name": "No active station mapped",
                    "station_code": None,
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "required": 0,
                    "completed": 0,
                    "completed_capped": 0,
                    "remaining": 0,
                    "is_complete": False,
                    "status": "NO_STATION_MAPPING",
                    "message": "No active station is mapped to this user. Map station access before weekly compliance can be calculated.",
                    **supervisors,
                }
            )
            continue

        for station in stations:
            unique_station_ids.add(int(station.id))
            completed = counts.get((int(inspector.id), int(station.id)), 0)
            completed_capped = min(completed, required)
            remaining = max(0, required - completed)
            is_complete = remaining == 0
            if only_pending and is_complete:
                continue
            rows.append(
                {
                    "inspector_id": inspector.id,
                    "inspector_name": inspector.name,
                    "emp_number": inspector.emp_number,
                    "username": inspector.username,
                    "role": _role_value(inspector),
                    "role_label": target["role_label"],
                    "station_id": station.id,
                    "station_name": station.station_name,
                    "station_code": station.station_code,
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "required": required,
                    "completed": completed,
                    "completed_capped": completed_capped,
                    "remaining": remaining,
                    "is_complete": is_complete,
                    "status": "COMPLETE" if is_complete else "PENDING",
                    "message": "Weekly target completed for this station." if is_complete else f"{remaining} inspection(s) pending for this station this week.",
                    **supervisors,
                }
            )

    rows.sort(key=lambda r: (r.get("is_complete", False), str(r.get("inspector_name") or ""), str(r.get("station_name") or "")))

    counted_rows = [row for row in rows if row["station_id"] is not None]
    issue_rows = [row for row in rows if row["status"] == "NO_STATION_MAPPING"]
    total_required = sum(int(row["required"] or 0) for row in counted_rows)
    total_completed = sum(int(row["completed_capped"] or 0) for row in counted_rows)
    total_remaining = sum(int(row["remaining"] or 0) for row in counted_rows)
    pending_rows = [row for row in counted_rows if int(row["remaining"] or 0) > 0]

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "current_role": _role_value(actor),
        "generated_for": {"id": actor.id, "name": actor.name, "role": _role_value(actor)},
        "summary": {
            "total_required": total_required,
            "total_completed": total_completed,
            "total_remaining": total_remaining,
            "total_rows": len(counted_rows),
            "pending_rows": len(pending_rows),
            "complete_rows": len([row for row in counted_rows if row["is_complete"]]),
            "issue_rows": len(issue_rows),
            "inspectors": len(inspectors),
            "stations": len(unique_station_ids),
            "is_complete": total_remaining == 0 and not issue_rows,
            "message": (
                "All station-wise weekly inspection targets are complete."
                if total_remaining == 0 and not issue_rows
                else f"{total_remaining} inspection(s) are still pending across {len(pending_rows)} station/user row(s)."
            ),
        },
        "rows": rows,
        "top_pending": pending_rows[:8],
        "report_path": "/inspections/weekly-compliance",
    }


@router.get("/summary")
def weekly_compliance_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = _build_weekly_report(db, user, only_pending=False)
    return {
        "week_start": report["week_start"],
        "week_end": report["week_end"],
        "current_role": report["current_role"],
        "generated_for": report["generated_for"],
        "summary": report["summary"],
        "top_pending": report["top_pending"],
        "report_path": report["report_path"],
    }


@router.get("/report")
def weekly_compliance_report(
    only_pending: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _build_weekly_report(db, user, only_pending=only_pending)
