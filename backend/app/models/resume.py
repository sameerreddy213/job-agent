import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Resume(Base):
    """One row per role category (e.g. SDE, Frontend, Java_Developer)."""

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    category: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", order_by="ResumeVersion.version_number"
    )


class ResumeVersion(Base):
    """An uploaded resume file version. Old versions are kept; one is current."""

    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    skills_detected: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    role_category: Mapped[str] = mapped_column(String, nullable=False)
    # Detected (rule-based) category from parsed resume text (Phase 5A).
    detected_category: Mapped[str | None] = mapped_column(String, nullable=True)
    categorization_confidence: Mapped[int | None] = mapped_column(nullable=True)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    resume: Mapped["Resume"] = relationship(back_populates="versions")
