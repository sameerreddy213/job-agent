import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Application(Base):
    """One application per job. Tracks the post-approval lifecycle.

    NOTE (Phase 8A): this engine *tracks* applications only. It never submits
    them — no browser automation, no Playwright.
    """

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="NOT_STARTED")
    resume_category: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    answers: Mapped[list["ApplicationAnswer"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationDocument(Base):
    """A document attached to an application (resume/cover letter/packet export),
    linked back to the generated Material it came from."""

    __tablename__ = "application_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)  # resume | cover_letter | packet
    fmt: Mapped[str] = mapped_column(String, nullable=False)   # txt | docx | pdf
    path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(back_populates="documents")


class ApplicationAnswer(Base):
    """Application question/answer captured from the generated materials."""

    __tablename__ = "application_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(back_populates="answers")


class ApplicationEvent(Base):
    """Append-only audit of application state transitions and notable events."""

    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    previous_state: Mapped[str | None] = mapped_column(String, nullable=True)
    new_state: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(back_populates="events")
