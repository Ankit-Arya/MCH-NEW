from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.models.all_models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserMe
from app.services.audit_service import audit_log

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        audit_log(db, actor=None, action="LOGIN_FAILED", entity_type="User", new_value={"username": payload.username})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user.last_login_at = datetime.utcnow()
    audit_log(db, actor=user, action="LOGIN_SUCCESS", entity_type="User", entity_id=user.id)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, extra={"role": user.role.code.value}), refresh_token=create_refresh_token(user.id))


@router.post("/refresh", response_model=TokenResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        user = db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise ValueError("Invalid user")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return TokenResponse(access_token=create_access_token(user.id, extra={"role": user.role.code.value}), refresh_token=create_refresh_token(user.id))


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_user)):
    return UserMe(id=user.id, username=user.username, name=user.name, role=user.role.code.value, permissions=[user.role.code.value])


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    return {"message": "Logged out. Remove token on client."}
