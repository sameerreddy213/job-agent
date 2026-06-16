"""Audit-log helper. Records who did what, when."""
from sqlalchemy.orm import Session

from .models.audit import AuditLog


def write_audit(
    db: Session,
    actor: str,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    payload: dict | None = None,
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            actor=actor,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            payload=payload or {},
        )
    )
    if commit:
        db.commit()
