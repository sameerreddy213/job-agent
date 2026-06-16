import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    company: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[str | None] = mapped_column(String, nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Recruiter/contact email parsed from the JD (for manual outreach).
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    remote_status: Mapped[str | None] = mapped_column(String, nullable=True)

    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="DISCOVERED")
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Telegram high-match notification de-dupe (Phase 6C).
    high_match_notified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Workflow snooze (Phase 7A) — keeps state but defers from the active queue.
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    score: Mapped["JobScore | None"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class JobScore(Base):
    __tablename__ = "job_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    freshers_score: Mapped[int] = mapped_column(nullable=False, server_default="0")
    skills_score: Mapped[int] = mapped_column(nullable=False, server_default="0")
    location_score: Mapped[int] = mapped_column(nullable=False, server_default="0")
    role_score: Mapped[int] = mapped_column(nullable=False, server_default="0")
    total_score: Mapped[int] = mapped_column(nullable=False, server_default="0")
    classification: Mapped[str] = mapped_column(String, nullable=False)
    matched_resume_category: Mapped[str | None] = mapped_column(String, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed_filters: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Resume intelligence (Phase 5A)
    resume_match_score: Mapped[int] = mapped_column(nullable=False, server_default="0")
    resume_confidence: Mapped[int] = mapped_column(nullable=False, server_default="0")
    matched_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    missing_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    resume_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_override: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped["Job"] = relationship(back_populates="score")


class RunHealth(Base):
    __tablename__ = "run_health"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    jobs_found: Mapped[int] = mapped_column(nullable=False, server_default="0")
    new_jobs: Mapped[int] = mapped_column(nullable=False, server_default="0")
    filtered: Mapped[int] = mapped_column(nullable=False, server_default="0")
    scored: Mapped[int] = mapped_column(nullable=False, server_default="0")
    errors: Mapped[int] = mapped_column(nullable=False, server_default="0")
    response_time_ms: Mapped[int] = mapped_column(nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String, nullable=False)  # HEALTHY|WARNING|FAILED
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
