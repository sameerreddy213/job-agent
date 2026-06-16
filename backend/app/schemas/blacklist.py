import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyBlacklistCreate(BaseModel):
    company: str
    reason: str | None = None


class CompanyBlacklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: str
    reason: str | None = None
    created_at: datetime


class KeywordBlacklistCreate(BaseModel):
    keyword: str
    applies_to: str = "both"  # title | description | both
    reason: str | None = None


class KeywordBlacklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keyword: str
    applies_to: str
    reason: str | None = None
    created_at: datetime
