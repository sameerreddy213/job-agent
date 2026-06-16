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
    # ATS integration (Phase 8B)
    ats_type: str = "UNKNOWN"
    ats_version: str | None = None
    application_url: str | None = None
    supports_easy_apply: bool = False
    requires_manual_fields: bool = True
    # Manual apply assistant (Phase 8C)
    ready_confirmed: bool = False
    ready_confirmed_at: datetime | None = None
    packet_generated_at: datetime | None = None
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


# --- ATS integration layer (Phase 8B) --- #
class ReadinessReport(BaseModel):
    application_id: uuid.UUID
    ready_score: int
    ready: bool
    missing_materials: bool
    missing_resume: bool
    missing_answers: bool
    manual_review_required: bool
    reasons: list[str] = []


class ReadinessItem(ApplicationOut):
    """An application enriched with its readiness summary (for the Ready Queue)."""

    ready_score: int
    ready: bool
    manual_review_required: bool


class AtsCount(BaseModel):
    ats_type: str
    count: int


class AtsBreakdown(BaseModel):
    total: int
    detected: int          # ats_type != UNKNOWN
    unknown: int           # ats_type == UNKNOWN
    ready_to_apply: int
    manual_review_required: int
    by_ats: list[AtsCount]


# --- Manual apply assistant (Phase 8C) --- #
class ChecklistItem(BaseModel):
    key: str
    label: str
    done: bool
    required: bool


class ChecklistOut(BaseModel):
    application_id: uuid.UUID
    items: list[ChecklistItem]
    complete: bool          # all required items done
    ready_confirmed: bool


class PacketOut(BaseModel):
    application_id: uuid.UUID
    generated: bool
    generated_at: datetime | None = None
    formats: list[str] = []


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
