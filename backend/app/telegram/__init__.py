"""Telegram notification system (Phase 6C) — notifications + read-only commands.

No approval actions. Token is env-only; chat_id + preferences live in the
telegram_settings table (dashboard-editable).
"""
from .client import token_configured
from .notifier import (
    is_enabled,
    notify_high_matches,
    notify_pipeline_failure,
    notify_security,
    notify_sheets_failure,
    send_daily_summary,
    send_evening_summary,
)
from .poller import poll_once

__all__ = [
    "token_configured",
    "is_enabled",
    "notify_high_matches",
    "notify_pipeline_failure",
    "notify_security",
    "notify_sheets_failure",
    "send_daily_summary",
    "send_evening_summary",
    "poll_once",
]
