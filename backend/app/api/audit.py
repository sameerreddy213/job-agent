from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.audit import AuditLog
from ..models.user import User
from ..schemas.audit import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    action: str | None = None,
    actor: str | None = None,
    entity: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    if entity_id:
        q = q.filter(AuditLog.entity_id == str(entity_id))
    return q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
