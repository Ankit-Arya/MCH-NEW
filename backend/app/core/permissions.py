from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.all_models import RoleCode, User, UserStationAccess, UserLineAccess, Station

ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.GM_OPS, RoleCode.HK_CELL_ADMIN}


def has_role(user: User, roles: set[RoleCode]) -> bool:
    return user.role.code in roles


def require_roles(user: User, roles: set[RoleCode]) -> None:
    if not has_role(user, roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def can_access_station(db: Session, user: User, station_id: int) -> bool:
    if user.role.code in ADMIN_ROLES:
        return True
    station_access = db.query(UserStationAccess).filter_by(user_id=user.id, station_id=station_id, is_active=True).first()
    if station_access:
        return True
    station = db.get(Station, station_id)
    if not station:
        return False
    line_access = db.query(UserLineAccess).filter_by(user_id=user.id, line_id=station.line_id, is_active=True).first()
    return bool(line_access)


def require_station_access(db: Session, user: User, station_id: int) -> None:
    if not can_access_station(db, user, station_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to selected station")
