from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Source(Base):
    """A configured job source (Greenhouse/Lever/Ashby; extensible)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # ats | company | board
    apply_policy: Mapped[str] = mapped_column(String, nullable=False, server_default="auto")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Connector config, e.g. {"boards": ["stripe", "airbnb"]}
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    # Source configuration metadata
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    rate_limit_per_min: Mapped[int | None] = mapped_column(nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
