from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRefreshSession(Base):
    """Server-side refresh-token session store.

    We never store the raw refresh token. Only a SHA-256 hash of the raw token and
    the JWT jti are stored. This allows logout/revocation/rotation while keeping
    the database safe if it is inspected.
    """

    __tablename__ = "user_refresh_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    refresh_token_jti: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    replaced_by_session_id: Mapped[int | None] = mapped_column(ForeignKey("user_refresh_sessions.id"), nullable=True)
    reuse_detected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user_agent: Mapped[str | None] = mapped_column(String(250), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("refresh_token_jti", name="uq_user_refresh_sessions_jti"),
        UniqueConstraint("refresh_token_hash", name="uq_user_refresh_sessions_hash"),
    )
