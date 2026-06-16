"""Read-only Telegram bot commands: /stats /health /sync-status /latest-jobs."""
from sqlalchemy.orm import Session

from ..constants import CLASS_AUTO, CLASS_REVIEW
from ..metrics import compute_metrics
from ..models.job import Job, RunHealth
from ..models.sync import SheetSyncRun
from . import client

HELP = "Commands: /stats /health /sync-status /latest-jobs"


def _stats(db: Session) -> str:
    m = compute_metrics(db)
    review = db.query(Job).filter(Job.archived.is_(False), Job.status == CLASS_REVIEW).count()
    auto = db.query(Job).filter(Job.archived.is_(False), Job.status == CLASS_AUTO).count()
    return (
        "Stats\n"
        f"Jobs found: {m['jobs_found']}\n"
        f"Filtered: {m['jobs_filtered']} | Scored: {m['jobs_scored']}\n"
        f"Review queue: {review} | Auto-eligible: {auto}\n"
        f"Pipeline runs: {m['pipeline_runs']} (failures: {m['pipeline_failures']})"
    )


def _health(db: Session) -> str:
    rows = db.query(RunHealth).order_by(RunHealth.run_at.desc()).all()
    latest: dict[str, RunHealth] = {}
    for r in rows:
        latest.setdefault(r.source, r)
    if not latest:
        return "Health: no runs yet."
    lines = [f"{name}: {r.status} (found {r.jobs_found}, err {r.errors})" for name, r in latest.items()]
    return "Source health\n" + "\n".join(lines)


def _sync_status(db: Session) -> str:
    last = db.query(SheetSyncRun).order_by(SheetSyncRun.run_at.desc()).first()
    if not last:
        return "Sheets: never synced."
    return (
        "Sheets sync\n"
        f"Status: {last.status}\n"
        f"Rows: {last.rows_written} | {last.duration_ms} ms\n"
        f"At: {last.run_at.isoformat()}"
    )


def _latest_jobs(db: Session) -> str:
    jobs = (
        db.query(Job)
        .filter(Job.archived.is_(False), Job.status.in_([CLASS_AUTO, CLASS_REVIEW]))
        .order_by(Job.discovered_at.desc())
        .limit(5)
        .all()
    )
    if not jobs:
        return "No actionable jobs."
    lines = []
    for j in jobs:
        score = j.score.total_score if j.score else "-"
        lines.append(f"[{score}] {j.title} @ {j.company} ({j.location or '-'})")
    return "Latest jobs\n" + "\n".join(lines)


DISPATCH = {
    "/stats": _stats,
    "/health": _health,
    "/sync-status": _sync_status,
    "/latest-jobs": _latest_jobs,
}


def handle_update(db: Session, update: dict) -> str | None:
    """Process one getUpdates entry. Returns the command handled, or None."""
    message = update.get("message") or update.get("channel_post") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", "")) if chat.get("id") is not None else ""
    if not text.startswith("/") or not chat_id:
        return None

    # Normalize "/stats@BotName" -> "/stats"
    cmd = text.split()[0].split("@")[0].lower()
    handler = DISPATCH.get(cmd)
    reply = handler(db) if handler else HELP
    client.send_message(reply, chat_id)
    return cmd
