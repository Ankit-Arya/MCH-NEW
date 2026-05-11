from sqlalchemy.orm import Session
from app.models.all_models import AuditLog, User


def audit_log(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role.code.value if actor and actor.role else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value_json=old_value,
            new_value_json=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
