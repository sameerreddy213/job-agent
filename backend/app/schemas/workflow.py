"""Phase 7B — workflow analytics & timeline response shapes."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimelineEvent(BaseModel):
    """A single workflow transition, enriched with job context for global feeds."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    company: str | None = None
    title: str | None = None
    previous_state: str | None = None
    new_state: str
    actor: str
    reason: str | None = None
    created_at: datetime


class StatePoint(BaseModel):
    state: str
    count: int


class DayCount(BaseModel):
    day: str
    count: int


class WorkflowAnalytics(BaseModel):
    """Aggregate workflow health over a trailing window."""

    days: int
    jobs_by_state: list[StatePoint]
    total_transitions: int
    approvals: int
    rejections: int
    snoozes: int
    archives: int
    decisions: int  # approvals + rejections + snoozes
    approval_pct: float
    rejection_pct: float
    snooze_pct: float
    avg_review_seconds: float | None  # None when no review decisions yet
    pending_review_trend: list[DayCount]  # jobs entering REVIEW_QUEUE per day


class ApprovalStats(BaseModel):
    """Decision counts and rates, plus per-day approved/rejected breakdown."""

    days: int
    approved: int
    rejected: int
    archived: int
    snoozed: int
    approval_rate: float
    rejection_rate: float
    approved_per_day: list[DayCount]
    rejected_per_day: list[DayCount]
