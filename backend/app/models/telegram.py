import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TelegramSettings(Base):
    """Singleton (id=1) — dashboard-editable Telegram config + notification prefs.

    The bot token is NEVER stored here (env-only secret). chat_id falls back to
    TELEGRAM_CHAT_ID env when null.
    """

    __tablename__ = "telegram_settings"
    __table_args__ = (CheckConstraint("id = 1", name="telegram_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    chat_id: Mapped[str | None] = mapped_column(String, nullable=True)

    pref_high_match: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    pref_daily: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    pref_evening: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    pref_pipeline_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    pref_sheets_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    pref_security: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # getUpdates polling offset.
    last_update_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class TelegramEvent(Base):
    """Log of outbound Telegram messages (drives metrics)."""

    __tablename__ = "telegram_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # sent | failed
    retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
