import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    file_path: str
    skills_detected: list
    role_category: str
    detected_category: str | None = None
    categorization_confidence: int | None = None
    upload_date: datetime
    is_current: bool


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    is_active: bool
    created_at: datetime
    current_version: ResumeVersionOut | None = None


class ResumeDetailOut(ResumeOut):
    versions: list[ResumeVersionOut] = []


class ResumeSummaryOut(BaseModel):
    """Dashboard view: current version, previous-version count, last updated."""

    category: str
    current_version: ResumeVersionOut | None = None
    previous_versions: int = 0
    last_updated: datetime | None = None
