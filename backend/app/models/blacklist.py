import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class CompanyBlacklist(Base):
    """Companies to exclude from discovery results."""

    __tablename__ = "company_blacklist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    company: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KeywordBlacklist(Base):
    """Keywords that, if present, exclude a job. applies_to: title|description|both."""

    __tablename__ = "keyword_blacklist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    keyword: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    applies_to: Mapped[str] = mapped_column(String, nullable=False, server_default="both")
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
