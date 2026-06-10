from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import false
from sqlalchemy.orm import Session

from app.models.access_control import UserSupervisorAccess
from app.models.all_models import (
    ContractStation,
    Inspection,
    RoleCode,
    Station,
    User,
    UserLineAccess,
    UserStationAccess,
)

ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.GM_OPS, RoleCode.HK_CELL_ADMIN}
MASTER_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}
LINE_MANAGER_ROLES = {RoleCode.AM_MGR_LINE, RoleCode.AM_MGR_HK}
DGM_ROLES = {RoleCode.DGM_LINE, RoleCode.DGM_HK}
GM_ROLES = {RoleCode.GM_OPS}


def role_code(user: User) -> RoleCode | None:
    return user.role.code if user and user.role else None


def has_role(user: User, roles: set[RoleCode]) -> bool:
    return role_code(user) in roles


def require_roles(user: User, roles: set[RoleCode]) -> None:
    if not has_role(user, roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def is_admin_scope(user: User) -> bool:
    return role_code(user) in ADMIN_ROLES


def get_direct_station_ids(db: Session, user_id: int) -> set[int]:
    """Stations directly mapped to the user, including stations from line mapping."""

    station_ids = {
        row.station_id
        for row in db.query(UserStationAccess.station_id)
        .filter(
            UserStationAccess.user_id == user_id,
            UserStationAccess.is_active.is_(True),
        )
        .all()
    }

    line_ids = [
        row.line_id
        for row in db.query(UserLineAccess.line_id)
        .filter(
            UserLineAccess.user_id == user_id,
            UserLineAccess.is_active.is_(True),
        )
        .all()
    ]
    if line_ids:
        station_ids.update(
            row.id
            for row in db.query(Station.id)
            .filter(Station.line_id.in_(line_ids), Station.is_active.is_(True))
            .all()
        )
    return station_ids


def get_descendant_user_ids(db: Session, supervisor_user_id: int) -> set[int]:
    """Return active subordinate user ids under this user, recursively.

    Example:
    DGM -> LM -> SM returns both the LM and the SM ids.
    """

    visited: set[int] = set()
    frontier: list[int] = [supervisor_user_id]

    while frontier:
        current = frontier.pop(0)
        rows = (
            db.query(UserSupervisorAccess.subordinate_user_id)
            .filter(
                UserSupervisorAccess.supervisor_user_id == current,
                UserSupervisorAccess.is_active.is_(True),
            )
            .all()
        )
        for (subordinate_id,) in rows:
            if subordinate_id == supervisor_user_id or subordinate_id in visited:
                continue
            visited.add(subordinate_id)
            frontier.append(subordinate_id)
    return visited


def get_scope_user_ids(db: Session, user: User, include_self: bool = True) -> set[int] | None:
    """User ids visible through reporting hierarchy.

    Admin roles return None meaning unrestricted. Non-admin users return themselves plus
    all recursive subordinates when include_self is true.
    """

    if is_admin_scope(user):
        return None

    ids = get_descendant_user_ids(db, user.id)
    if include_self:
        ids.add(user.id)
    return ids


def get_accessible_station_ids(db: Session, user: User) -> set[int] | None:
    """Return None for all-station access; otherwise station ids mapped to user/tree.

    This is used for station dropdowns and station-start permission. It is intentionally
    not used alone for LM/DGM inspection visibility, because LM/DGM visibility must be
    based on subordinate submitters, not merely station overlap.
    """

    if is_admin_scope(user):
        return None

    station_ids = get_direct_station_ids(db, user.id)
    for subordinate_user_id in get_descendant_user_ids(db, user.id):
        station_ids.update(get_direct_station_ids(db, subordinate_user_id))
    return station_ids


def get_accessible_contract_ids(db: Session, user: User) -> set[int] | None:
    if is_admin_scope(user):
        return None

    station_ids = get_accessible_station_ids(db, user) or set()
    if not station_ids:
        return set()

    return {
        row.contract_id
        for row in db.query(ContractStation.contract_id)
        .filter(
            ContractStation.station_id.in_(station_ids),
            ContractStation.is_active.is_(True),
        )
        .all()
    }


def can_access_station(db: Session, user: User, station_id: int) -> bool:
    station_ids = get_accessible_station_ids(db, user)
    if station_ids is None:
        return True
    return int(station_id) in station_ids


def require_station_access(db: Session, user: User, station_id: int) -> None:
    if not can_access_station(db, user, station_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to selected station")


def get_hierarchy_submitter_ids(db: Session, user: User, include_self: bool = True) -> set[int] | None:
    """Submitter ids that should drive LM/DGM visibility.

    For admin users None means unrestricted. For non-admin users this is the recursive
    reporting tree. This function is separated from station scope so a DGM does not see
    every inspection of a station only because one subordinate SM is mapped there.
    """

    return get_scope_user_ids(db, user, include_self=include_self)


def apply_inspection_scope(query, db: Session, user: User):
    """Apply strict inspection visibility.

    Rules:
    - Admin/HK Cell/GM Ops: all inspections.
    - LM/DGM or any user with active subordinates: only inspections submitted by
      self or recursive subordinates. This is the key hierarchy rule.
    - SM/EIT or users without subordinates: station scope, so an SM mapped to a
      station can see inspections for that station.
    - If no mapping exists: only own submitted inspections.
    """

    if is_admin_scope(user):
        return query

    descendants = get_descendant_user_ids(db, user.id)
    if descendants:
        submitter_ids = set(descendants)
        submitter_ids.add(user.id)
        return query.filter(Inspection.submitted_by.in_(submitter_ids))

    station_ids = get_direct_station_ids(db, user.id)
    if station_ids:
        return query.filter(Inspection.station_id.in_(station_ids))

    return query.filter(Inspection.submitted_by == user.id)


def can_access_inspection(db: Session, user: User, inspection: Inspection) -> bool:
    if is_admin_scope(user):
        return True

    descendants = get_descendant_user_ids(db, user.id)
    if descendants:
        submitter_ids = set(descendants)
        submitter_ids.add(user.id)
        return inspection.submitted_by in submitter_ids

    station_ids = get_direct_station_ids(db, user.id)
    if station_ids and inspection.station_id in station_ids:
        return True

    return inspection.submitted_by == user.id


def require_inspection_access(db: Session, user: User, inspection: Inspection) -> None:
    if not can_access_inspection(db, user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this inspection")


def apply_station_scope(query, station_column, db: Session, user: User):
    if is_admin_scope(user):
        return query

    station_ids = get_accessible_station_ids(db, user) or set()
    if not station_ids:
        return query.filter(false())
    return query.filter(station_column.in_(station_ids))


def apply_contract_scope(query, contract_column, db: Session, user: User):
    if is_admin_scope(user):
        return query

    contract_ids = get_accessible_contract_ids(db, user) or set()
    if not contract_ids:
        return query.filter(false())
    return query.filter(contract_column.in_(contract_ids))


def allowed_review_statuses(user: User) -> list:
    code = role_code(user)
    from app.models.all_models import InspectionStatus

    if code in ADMIN_ROLES:
        return [
            InspectionStatus.UNDER_LINE_MANAGER_REVIEW,
            InspectionStatus.LINE_MANAGER_RECOMMENDED,
            InspectionStatus.GM_REVIEW_REQUIRED,
        ]
    if code in LINE_MANAGER_ROLES:
        return [InspectionStatus.UNDER_LINE_MANAGER_REVIEW]
    if code in DGM_ROLES:
        return [InspectionStatus.LINE_MANAGER_RECOMMENDED]
    if code in GM_ROLES:
        return [InspectionStatus.GM_REVIEW_REQUIRED]
    return []


def apply_review_scope(query, db: Session, user: User):
    statuses = allowed_review_statuses(user)
    if not statuses:
        return query.filter(false())
    query = query.filter(Inspection.status.in_(statuses))
    return apply_inspection_scope(query, db, user)
