import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor: str
    action: str
    entity: str | None = None
    entity_id: str | None = None
    payload: dict
    created_at: datetime
