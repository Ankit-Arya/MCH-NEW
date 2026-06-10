from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import (
    MASTER_ADMIN_ROLES,
    get_accessible_station_ids,
    get_descendant_user_ids,
    get_direct_station_ids,
    get_scope_user_ids,
    require_roles,
)
from app.models.access_control import UserSupervisorAccess
from app.models.all_models import Line, RoleCode, Station, User, UserLineAccess, UserStationAccess
from app.schemas.access_control import LineAccessUpdate, ReportingAccessUpdate, StationAccessUpdate
from app.services.audit_service import audit_log

router = APIRouter()


def _require_manage(user: User) -> None:
    require_roles(user, MASTER_ADMIN_ROLES)


def _user_row(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "emp_number": user.emp_number,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "role": user.role.code.value if user.role else None,
        "is_active": user.is_active,
    }


def _ensure_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="Active user not found")
    return user


def _ensure_no_reporting_cycle(db: Session, supervisor_user_id: int, subordinate_user_id: int) -> None:
    if supervisor_user_id == subordinate_user_id:
        raise HTTPException(status_code=422, detail="A user cannot report to themselves")

    # If supervisor already appears below subordinate, adding subordinate below supervisor creates a cycle.
    descendants_of_subordinate = get_descendant_user_ids(db, subordinate_user_id)
    if supervisor_user_id in descendants_of_subordinate:
        raise HTTPException(status_code=422, detail="Reporting hierarchy cycle detected")


def _replace_station_access(db: Session, payload: StationAccessUpdate, actor: User) -> dict[str, Any]:
    target = _ensure_user(db, payload.user_id)
    station_ids = set(payload.station_ids or [])
    if station_ids:
        existing_station_ids = {row.id for row in db.query(Station.id).filter(Station.id.in_(station_ids)).all()}
        missing = station_ids - existing_station_ids
        if missing:
            raise HTTPException(status_code=404, detail=f"Station id(s) not found: {sorted(missing)}")

    existing_rows = db.query(UserStationAccess).filter(UserStationAccess.user_id == target.id).all()
    existing_by_station = {row.station_id: row for row in existing_rows}

    for row in existing_rows:
        row.is_active = row.station_id in station_ids

    for station_id in station_ids:
        if station_id not in existing_by_station:
            db.add(UserStationAccess(user_id=target.id, station_id=station_id, is_active=True))

    audit_log(
        db,
        actor=actor,
        action="ACCESS_STATION_MAPPING_UPDATED",
        entity_type="User",
        entity_id=target.id,
        new_value={"station_ids": sorted(station_ids)},
    )
    return {"message": "Station access updated", "user_id": target.id, "station_ids": sorted(station_ids)}


def _replace_line_access(db: Session, payload: LineAccessUpdate, actor: User) -> dict[str, Any]:
    target = _ensure_user(db, payload.user_id)
    line_ids = set(payload.line_ids or [])
    if line_ids:
        existing_line_ids = {row.id for row in db.query(Line.id).filter(Line.id.in_(line_ids)).all()}
        missing = line_ids - existing_line_ids
        if missing:
            raise HTTPException(status_code=404, detail=f"Line id(s) not found: {sorted(missing)}")

    existing_rows = db.query(UserLineAccess).filter(UserLineAccess.user_id == target.id).all()
    existing_by_line = {row.line_id: row for row in existing_rows}

    for row in existing_rows:
        row.is_active = row.line_id in line_ids

    for line_id in line_ids:
        if line_id not in existing_by_line:
            db.add(UserLineAccess(user_id=target.id, line_id=line_id, is_active=True))

    audit_log(
        db,
        actor=actor,
        action="ACCESS_LINE_MAPPING_UPDATED",
        entity_type="User",
        entity_id=target.id,
        new_value={"line_ids": sorted(line_ids)},
    )
    return {"message": "Line access updated", "user_id": target.id, "line_ids": sorted(line_ids)}


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)

    users = db.query(User).options(joinedload(User.role)).filter(User.is_active.is_(True)).order_by(User.name).all()
    station_access = db.query(UserStationAccess).filter(UserStationAccess.is_active.is_(True)).all()
    line_access = db.query(UserLineAccess).filter(UserLineAccess.is_active.is_(True)).all()
    reporting_links = (
        db.query(UserSupervisorAccess)
        .filter(UserSupervisorAccess.is_active.is_(True))
        .order_by(UserSupervisorAccess.supervisor_user_id, UserSupervisorAccess.subordinate_user_id)
        .all()
    )

    return {
        "roles": [role.value for role in RoleCode],
        "users": [_user_row(u) for u in users],
        "stations": db.query(Station).filter(Station.is_active.is_(True)).order_by(Station.station_name).all(),
        "lines": db.query(Line).filter(Line.is_active.is_(True)).order_by(Line.line_code).all(),
        "station_access": [
            {"id": row.id, "user_id": row.user_id, "station_id": row.station_id}
            for row in station_access
        ],
        "line_access": [
            {"id": row.id, "user_id": row.user_id, "line_id": row.line_id}
            for row in line_access
        ],
        "reporting_links": [
            {
                "id": row.id,
                "supervisor_user_id": row.supervisor_user_id,
                "subordinate_user_id": row.subordinate_user_id,
                "relation_type": row.relation_type,
            }
            for row in reporting_links
        ],
    }


@router.get("/my-scope")
def my_scope(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    station_ids = get_accessible_station_ids(db, user)
    scope_user_ids = get_scope_user_ids(db, user, include_self=True)
    return {
        "all_stations": station_ids is None,
        "station_ids": sorted(station_ids or []),
        "scope_user_ids": None if scope_user_ids is None else sorted(scope_user_ids),
        "direct_station_ids": sorted(get_direct_station_ids(db, user.id)),
        "descendant_user_ids": sorted(get_descendant_user_ids(db, user.id)),
        "role": user.role.code.value if user.role else None,
    }


@router.put("/station-access")
def set_station_access(payload: StationAccessUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    result = _replace_station_access(db, payload, user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate station mapping") from exc
    return result


@router.put("/line-access")
def set_line_access(payload: LineAccessUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    result = _replace_line_access(db, payload, user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate line mapping") from exc
    return result


@router.put("/reporting-links")
def set_reporting_links(payload: ReportingAccessUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    supervisor = _ensure_user(db, payload.supervisor_user_id)
    subordinate_ids = set(payload.subordinate_user_ids or [])

    for subordinate_id in subordinate_ids:
        _ensure_user(db, subordinate_id)
        _ensure_no_reporting_cycle(db, supervisor.id, subordinate_id)

    existing_rows = (
        db.query(UserSupervisorAccess)
        .filter(
            UserSupervisorAccess.supervisor_user_id == supervisor.id,
            UserSupervisorAccess.relation_type == payload.relation_type,
        )
        .all()
    )
    existing_by_subordinate = {row.subordinate_user_id: row for row in existing_rows}

    for row in existing_rows:
        row.is_active = row.subordinate_user_id in subordinate_ids

    for subordinate_id in subordinate_ids:
        if subordinate_id not in existing_by_subordinate:
            db.add(
                UserSupervisorAccess(
                    supervisor_user_id=supervisor.id,
                    subordinate_user_id=subordinate_id,
                    relation_type=payload.relation_type,
                    is_active=True,
                )
            )

    audit_log(
        db,
        actor=user,
        action="ACCESS_REPORTING_MAPPING_UPDATED",
        entity_type="User",
        entity_id=supervisor.id,
        new_value={"subordinate_user_ids": sorted(subordinate_ids), "relation_type": payload.relation_type},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate reporting mapping") from exc

    return {
        "message": "Reporting hierarchy updated",
        "supervisor_user_id": supervisor.id,
        "subordinate_user_ids": sorted(subordinate_ids),
        "relation_type": payload.relation_type,
    }
