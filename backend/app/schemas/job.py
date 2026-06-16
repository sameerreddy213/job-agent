import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    freshers_score: int
    skills_score: int
    location_score: int
    role_score: int
    total_score: int
    classification: str
    matched_resume_category: str | None = None
    reasoning: str | None = None
    passed_filters: bool
    # Resume intelligence (Phase 5A)
    resume_match_score: int = 0
    resume_confidence: int = 0
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    resume_reasoning: str | None = None
    resume_override: bool = False


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str | None = None
    fingerprint: str
    company: str
    title: str
    location: str | None = None
    experience: str | None = None
    apply_url: str | None = None
    posted_date: datetime | None = None
    employment_type: str | None = None
    remote_status: str | None = None
    status: str
    discovered_at: datetime
    archived: bool
    score: ScoreOut | None = None


class JobDetailOut(JobOut):
    description: str | None = None


class JobStateHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_state: str | None = None
    new_state: str
    actor: str
    reason: str | None = None
    created_at: datetime
