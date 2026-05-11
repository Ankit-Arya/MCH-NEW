from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.core.security import get_password_hash
from app.models.all_models import RoleCode, User, Role, UserStationAccess, UserLineAccess

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    emp_number: str | None = None
    email: str | None = None
    mobile: str | None = None
    role_code: RoleCode
    station_ids: list[int] = []
    line_ids: list[int] = []


@router.get("")
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN, RoleCode.GM_OPS})
    return db.query(User).all()


@router.post("")
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    role = db.query(Role).filter(Role.code == payload.role_code).first()
    new_user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        emp_number=payload.emp_number,
        email=payload.email,
        mobile=payload.mobile,
        role_id=role.id,
    )
    db.add(new_user)
    db.flush()
    for station_id in payload.station_ids:
        db.add(UserStationAccess(user_id=new_user.id, station_id=station_id))
    for line_id in payload.line_ids:
        db.add(UserLineAccess(user_id=new_user.id, line_id=line_id))
    db.commit()
    db.refresh(new_user)
    return new_user
