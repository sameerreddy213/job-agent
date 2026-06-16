"""High-level Telegram notifications. Each logs a TelegramEvent (for metrics)."""
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import settings
from ..constants import CLASS_AUTO, CLASS_REVIEW
from ..models.job import Job
from ..models.telegram import TelegramEvent, TelegramSettings
from . import client


def get_settings(db: Session) -> TelegramSettings:
    s = db.get(TelegramSettings, 1)
    if s is None:
        s = TelegramSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def effective_chat_id(s: TelegramSettings) -> str:
    return (s.chat_id or settings.TELEGRAM_CHAT_ID or "").strip()


def is_enabled(db: Session) -> bool:
    s = get_settings(db)
    return bool(client.token_configured() and s.enabled and effective_chat_id(s))


def _send(db: Session, kind: str, text: str, chat_id: str) -> bool:
    ok, retries, error = client.send_message(text, chat_id)
    db.add(TelegramEvent(kind=kind, status="sent" if ok else "failed", retries=retries, error=error))
    db.commit()
    return ok


# --------------------------------------------------------------------------- #
# Event notifications
# --------------------------------------------------------------------------- #
def notify_high_matches(db: Session) -> int:
    """Send for AUTO_APPROVE_ELIGIBLE jobs not yet notified. Returns count sent."""
    s = get_settings(db)
    if not (is_enabled(db) and s.pref_high_match):
        return 0
    chat = effective_chat_id(s)
    jobs = (
        db.query(Job)
        .filter(Job.status == CLASS_AUTO, Job.high_match_notified.is_(False), Job.archived.is_(False))
        .all()
    )
    sent = 0
    for j in jobs:
        sc = j.score
        text = (
            "High match job (90+)\n"
            f"Company: {j.company}\n"
            f"Role: {j.title}\n"
            f"Location: {j.location or '-'}\n"
            f"Score: {sc.total_score if sc else '-'}\n"
            f"Resume: {sc.matched_resume_category if sc else '-'}\n"
            f"Apply: {j.apply_url or '-'}"
        )
        _send(db, "high_match", text, chat)
        j.high_match_notified = True  # mark attempted to avoid re-send loops
        sent += 1
    db.commit()
    return sent


def notify_pipeline_failure(db: Session, source: str, error: str, ts: datetime) -> None:
    s = get_settings(db)
    if not (is_enabled(db) and s.pref_pipeline_failure):
        return
    text = f"Pipeline failure\nSource: {source}\nError: {error or '-'}\nTime: {ts.isoformat()}"
    _send(db, "pipeline_failure", text, effective_chat_id(s))


def notify_sheets_failure(db: Session, result: dict) -> None:
    s = get_settings(db)
    if not (is_enabled(db) and s.pref_sheets_failure):
        return
    text = (
        "Google Sheets sync failure\n"
        f"Error: {result.get('error', '-')}\n"
        f"Rows written: {result.get('rows_written', 0)}\n"
        f"Duration: {result.get('duration_ms', 0)} ms"
    )
    _send(db, "sheets_failure", text, effective_chat_id(s))


def notify_security(db: Session, user: str, ts: datetime) -> None:
    s = get_settings(db)
    if not (is_enabled(db) and s.pref_security):
        return
    text = f"Security alert: refresh token reuse detected\nUser: {user}\nTime: {ts.isoformat()}"
    _send(db, "security", text, effective_chat_id(s))


# --------------------------------------------------------------------------- #
# Scheduled summaries
# --------------------------------------------------------------------------- #
def _summary_metrics(db: Session) -> dict:
    from ..metrics import compute_metrics

    m = compute_metrics(db)
    review = db.query(Job).filter(Job.archived.is_(False), Job.status == CLASS_REVIEW).count()
    auto = db.query(Job).filter(Job.archived.is_(False), Job.status == CLASS_AUTO).count()
    return {**m, "review_queue": review, "auto_eligible": auto}


def send_daily_summary(db: Session) -> None:
    s = get_settings(db)
    if not (is_enabled(db) and s.pref_daily):
        return
    m = _summary_metrics(db)
    sync = "ok" if m["sync_failure"] == 0 else "errors"
    text = (
        "Daily summary\n"
        f"Jobs found: {m['jobs_found']}\n"
        f"Jobs filtered: {m['jobs_filtered']}\n"
        f"Jobs scored: {m['jobs_scored']}\n"
        f"Review queue: {m['review_queue']}\n"
        f"Auto-approve eligible: {m['auto_eligible']}\n"
        f"Sheets sync: {sync} ({m['sync_success']} ok / {m['sync_failure']} failed)"
    )
    _send(db, "daily_summary", text, effective_chat_id(s))


def send_evening_summary(db: Session) -> None:
    s = get_settings(db)
    if not (is_enabled(db) and s.pref_evening):
        return
    from ..models.job import RunHealth

    m = _summary_metrics(db)
    rows = db.query(RunHealth).order_by(RunHealth.run_at.desc()).all()
    latest: dict[str, RunHealth] = {}
    for r in rows:
        latest.setdefault(r.source, r)
    health = "\n".join(f"  {name}: {r.status} ({r.errors} err)" for name, r in latest.items()) or "  none"
    text = (
        "Evening summary\n"
        f"Jobs found: {m['jobs_found']}\n"
        f"Jobs filtered: {m['jobs_filtered']}\n"
        f"Jobs scored: {m['jobs_scored']}\n"
        f"Review queue: {m['review_queue']}\n"
        f"Auto-approve eligible: {m['auto_eligible']}\n"
        f"Pipeline failures: {m['pipeline_failures']}\n"
        f"Source health:\n{health}"
    )
    _send(db, "evening_summary", text, effective_chat_id(s))
