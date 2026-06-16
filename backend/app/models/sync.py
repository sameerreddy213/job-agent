import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SyncState(Base):
    """Singleton (id=1) holding incremental-sync cursors."""

    __tablename__ = "sync_state"
    __table_args__ = (CheckConstraint("id = 1", name="sync_state_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    jobs_cursor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runs_cursor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SheetSyncRun(Base):
    """Log of each Sheets sync attempt (for status + metrics)."""

    __tablename__ = "sheet_sync_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)  # success | failed | skipped
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tabs: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
