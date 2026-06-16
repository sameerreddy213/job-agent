import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Material(Base):
    """Generated application materials for a job (one current packet per job)."""

    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    resume_category: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_letter_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_answers: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    txt_path: Mapped[str | None] = mapped_column(String, nullable=True)
    docx_path: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
