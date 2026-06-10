from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.core.security import get_password_hash
from app.models.all_models import Role, RoleCode, User, UserLineAccess, UserStationAccess
from app.services.audit_service import audit_log

router = APIRouter()

MANAGE_USER_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}
VIEW_USER_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN, RoleCode.GM_OPS}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., min_length=2, max_length=150)
    emp_number: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=150)
    mobile: str | None = Field(default=None, max_length=20)
    role_code: RoleCode
    station_ids: list[int] = []
    line_ids: list[int] = []
    is_active: bool = True

    @field_validator("username", "name", "emp_number", "email", "mobile", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    emp_number: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=150)
    mobile: str | None = Field(default=None, max_length=20)
    role_code: RoleCode | None = None
    is_active: bool | None = None

    @field_validator("username", "name", "emp_number", "email", "mobile", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class PasswordReset(BaseModel):
    password: str = Field(..., min_length=6, max_length=128)


class UserStatusUpdate(BaseModel):
    is_active: bool


def _user_row(user: User) -> dict:
    return {
        "id": user.id,
        "emp_number": user.emp_number,
        "name": user.name,
        "email": user.email,
        "mobile": user.mobile,
        "username": user.username,
        "role_id": user.role_id,
        "role": user.role.code.value if user.role else None,
        "role_name": user.role.name if user.role else None,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _require_manage(actor: User) -> None:
    require_roles(actor, MANAGE_USER_ROLES)


def _get_role(db: Session, role_code: RoleCode) -> Role:
    role = db.query(Role).filter(Role.code == role_code).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_code.value}")
    return role


def _ensure_unique_user_fields(db: Session, payload_username: str | None, payload_email: str | None, exclude_user_id: int | None = None) -> None:
    if payload_username:
        q = db.query(User).filter(User.username == payload_username)
        if exclude_user_id:
            q = q.filter(User.id != exclude_user_id)
        if q.first():
            raise HTTPException(status_code=409, detail="Username already exists")

    if payload_email:
        q = db.query(User).filter(User.email == payload_email)
        if exclude_user_id:
            q = q.filter(User.id != exclude_user_id)
        if q.first():
            raise HTTPException(status_code=409, detail="Email already exists")


def _replace_initial_access(db: Session, target_user_id: int, station_ids: list[int], line_ids: list[int]) -> None:
    for station_id in station_ids or []:
        db.add(UserStationAccess(user_id=target_user_id, station_id=station_id, is_active=True))
    for line_id in line_ids or []:
        db.add(UserLineAccess(user_id=target_user_id, line_id=line_id, is_active=True))


@router.get("")
def list_users(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, VIEW_USER_ROLES)
    query = db.query(User).options(joinedload(User.role)).order_by(User.name.asc())
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    return [_user_row(row) for row in query.all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    _ensure_unique_user_fields(db, payload.username, payload.email)
    role = _get_role(db, payload.role_code)

    new_user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        emp_number=payload.emp_number or None,
        email=payload.email or None,
        mobile=payload.mobile or None,
        role_id=role.id,
        is_active=payload.is_active,
    )
    db.add(new_user)
    db.flush()
    _replace_initial_access(db, new_user.id, payload.station_ids, payload.line_ids)
    audit_log(
        db,
        actor=user,
        action="USER_CREATED_BY_ADMIN",
        entity_type="User",
        entity_id=new_user.id,
        new_value={"username": new_user.username, "role": role.code.value},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate username/email or access mapping") from exc
    db.refresh(new_user)
    return _user_row(new_user)


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_unique_user_fields(db, payload.username, payload.email, exclude_user_id=user_id)

    if payload.username is not None:
        target.username = payload.username
    if payload.name is not None:
        target.name = payload.name
    if payload.emp_number is not None:
        target.emp_number = payload.emp_number or None
    if payload.email is not None:
        target.email = payload.email or None
    if payload.mobile is not None:
        target.mobile = payload.mobile or None
    if payload.role_code is not None:
        target.role_id = _get_role(db, payload.role_code).id
    if payload.is_active is not None:
        if target.id == user.id and payload.is_active is False:
            raise HTTPException(status_code=422, detail="You cannot deactivate your own logged-in account")
        target.is_active = payload.is_active
    target.updated_at = datetime.utcnow()

    audit_log(
        db,
        actor=user,
        action="USER_UPDATED_BY_ADMIN",
        entity_type="User",
        entity_id=target.id,
        new_value=payload.model_dump(exclude_unset=True),
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate username or email") from exc
    db.refresh(target)
    return _user_row(target)


@router.put("/{user_id}/password")
def reset_password(user_id: int, payload: PasswordReset, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.password_hash = get_password_hash(payload.password)
    target.updated_at = datetime.utcnow()
    audit_log(db, actor=user, action="USER_PASSWORD_RESET_BY_ADMIN", entity_type="User", entity_id=target.id)
    db.commit()
    return {"message": "Password reset successfully", "user_id": target.id}


@router.put("/{user_id}/status")
def set_user_status(user_id: int, payload: UserStatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id and payload.is_active is False:
        raise HTTPException(status_code=422, detail="You cannot deactivate your own logged-in account")
    target.is_active = payload.is_active
    target.updated_at = datetime.utcnow()
    audit_log(
        db,
        actor=user,
        action="USER_STATUS_UPDATED_BY_ADMIN",
        entity_type="User",
        entity_id=target.id,
        new_value={"is_active": payload.is_active},
    )
    db.commit()
    return _user_row(target)
