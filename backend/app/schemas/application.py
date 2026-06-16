"""Phase 8A — application engine response/request shapes."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID | None = None
    kind: str
    fmt: str
    path: str | None = None
    created_at: datetime


class ApplicationAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    answer: str | None = None
    created_at: datetime


class ApplicationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_state: str | None = None
    new_state: str
    actor: str
    reason: str | None = None
    created_at: datetime


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    material_id: uuid.UUID | None = None
    status: str
    resume_category: str | None = None
    notes: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Denormalised job context for list views (filled by the API).
    company: str | None = None
    title: str | None = None


class ApplicationDetailOut(ApplicationOut):
    documents: list[ApplicationDocumentOut] = []
    answers: list[ApplicationAnswerOut] = []
    events: list[ApplicationEventOut] = []


class CreateApplicationBody(BaseModel):
    job_id: uuid.UUID


class UpdateApplicationBody(BaseModel):
    notes: str | None = None
    resume_category: str | None = None


class TransitionBody(BaseModel):
    new_state: str
    reason: str | None = None


class StateCount(BaseModel):
    state: str
    count: int


class ApplicationAnalytics(BaseModel):
    total: int
    by_state: list[StateCount]
    created: int
    submitted: int
    interviews: int
    assessments: int
    offers: int
    rejections: int
    accepted: int
    withdrawn: int
    # Funnel conversion rates (%).
    submit_rate: float       # submitted / created
    interview_rate: float    # interviews / submitted
    offer_rate: float        # offers / submitted
    acceptance_rate: float   # accepted / offers
