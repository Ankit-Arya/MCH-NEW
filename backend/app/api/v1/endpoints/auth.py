from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_token_id,
    hash_token,
    verify_password,
)
from app.models.all_models import User
from app.models.auth_session import UserRefreshSession
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserMe
from app.services.audit_service import audit_log

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.utcnow()


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:50]
    if request.client:
        return request.client.host[:50]
    return None


def _user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    return value[:250] if value else None


def _refresh_expires_at() -> datetime:
    return _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def _issue_token_pair(db: Session, user: User, request: Request) -> tuple[TokenResponse, UserRefreshSession]:
    token_id = generate_token_id()
    refresh_token = create_refresh_token(user.id, token_id=token_id)
    refresh_session = UserRefreshSession(
        user_id=user.id,
        refresh_token_jti=token_id,
        refresh_token_hash=hash_token(refresh_token),
        issued_at=_utcnow(),
        expires_at=_refresh_expires_at(),
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    db.add(refresh_session)
    db.flush()

    access_token = create_access_token(user.id, extra={"role": user.role.code.value})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token), refresh_session


def _extract_refresh_token(payload: RefreshRequest | None, token: str | None) -> str:
    refresh_token = payload.refresh_token if payload else token
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token is required")
    return refresh_token


def _decode_refresh_payload(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        if not payload.get("jti"):
            raise ValueError("Missing token id")
        return payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")


def _revoke_active_sessions_for_user(db: Session, user_id: int, now: datetime) -> None:
    sessions = (
        db.query(UserRefreshSession)
        .filter(
            UserRefreshSession.user_id == user_id,
            UserRefreshSession.revoked_at.is_(None),
        )
        .all()
    )
    for session in sessions:
        session.revoked_at = now


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        audit_log(db, actor=None, action="LOGIN_FAILED", entity_type="User", new_value={"username": payload.username})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login_at = _utcnow()
    tokens, _ = _issue_token_pair(db, user, request)
    audit_log(
        db,
        actor=user,
        action="LOGIN_SUCCESS",
        entity_type="User",
        entity_id=user.id,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    payload: RefreshRequest | None = Body(default=None),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    refresh_token = _extract_refresh_token(payload, token)
    jwt_payload = _decode_refresh_payload(refresh_token)

    user = db.get(User, int(jwt_payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    now = _utcnow()
    refresh_hash = hash_token(refresh_token)
    session = (
        db.query(UserRefreshSession)
        .filter(
            UserRefreshSession.user_id == user.id,
            UserRefreshSession.refresh_token_jti == jwt_payload["jti"],
            UserRefreshSession.refresh_token_hash == refresh_hash,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if session.revoked_at is not None:
        session.reuse_detected_at = now
        _revoke_active_sessions_for_user(db, user.id, now)
        audit_log(
            db,
            actor=user,
            action="REFRESH_TOKEN_REUSE_DETECTED",
            entity_type="UserRefreshSession",
            entity_id=session.id,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected. Please login again.")

    if session.expires_at <= now:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    session.revoked_at = now
    session.last_used_at = now
    tokens, new_session = _issue_token_pair(db, user, request)
    session.replaced_by_session_id = new_session.id

    audit_log(
        db,
        actor=user,
        action="REFRESH_TOKEN_ROTATED",
        entity_type="UserRefreshSession",
        entity_id=session.id,
        new_value={"new_session_id": new_session.id},
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    db.commit()
    return tokens


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_user)):
    return UserMe(id=user.id, username=user.username, name=user.name, role=user.role.code.value, permissions=[user.role.code.value])


@router.post("/logout")
def logout(
    request: Request,
    payload: RefreshRequest | None = Body(default=None),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    refresh_token = payload.refresh_token if payload else token
    if not refresh_token:
        return {"message": "Logged out. Remove token on client."}

    try:
        jwt_payload = _decode_refresh_payload(refresh_token)
        session = (
            db.query(UserRefreshSession)
            .filter(
                UserRefreshSession.refresh_token_jti == jwt_payload["jti"],
                UserRefreshSession.refresh_token_hash == hash_token(refresh_token),
            )
            .first()
        )
        if session and session.revoked_at is None:
            session.revoked_at = _utcnow()
            user = db.get(User, session.user_id)
            audit_log(
                db,
                actor=user,
                action="LOGOUT_REFRESH_SESSION_REVOKED",
                entity_type="UserRefreshSession",
                entity_id=session.id,
                ip_address=_client_ip(request),
                user_agent=_user_agent(request),
            )
            db.commit()
    except Exception:
        # Logout should be idempotent. The client will still remove local tokens.
        db.rollback()

    return {"message": "Logged out. Refresh session revoked on server if it existed."}
