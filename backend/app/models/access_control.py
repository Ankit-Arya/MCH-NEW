from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserSupervisorAccess(Base):
    """Admin-maintained reporting hierarchy.

    Examples:
    - Line Manager -> Station Manager
    - DGM -> Line Manager
    - GM/Ops -> DGM

    The application uses this table to derive a user's inspection visibility scope.
    """

    __tablename__ = "user_supervisor_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supervisor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    subordinate_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(40), default="REPORTING", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    supervisor = relationship("User", foreign_keys=[supervisor_user_id])
    subordinate = relationship("User", foreign_keys=[subordinate_user_id])

    __table_args__ = (
        UniqueConstraint(
            "supervisor_user_id",
            "subordinate_user_id",
            "relation_type",
            name="uq_user_supervisor_subordinate_relation",
        ),
    )
