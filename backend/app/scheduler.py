"""APScheduler-based discovery scheduler (runs in the worker container).

Also writes a heartbeat file every minute so the container health check can
verify liveness even between hourly pipeline runs.
"""
import logging
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .database import SessionLocal
from .models.job import RunHealth
from .pipeline.runner import run_pipeline
from .sheets import is_configured, sync_all

logger = logging.getLogger("worker")
IST = ZoneInfo("Asia/Kolkata")

HEARTBEAT_FILE = "/tmp/worker.heartbeat"


def _heartbeat() -> None:
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except OSError:
        pass


def _post_run_notifications(db, summary: dict) -> None:
    """High-match alerts + per-source pipeline-failure alerts (best-effort)."""
    try:
        from .telegram import notify_high_matches, notify_pipeline_failure

        notify_high_matches(db)
        for run in summary.get("runs", []):
            if run.get("status") == "FAILED":
                rh = (
                    db.query(RunHealth)
                    .filter(RunHealth.source == run["source"])
                    .order_by(RunHealth.run_at.desc())
                    .first()
                )
                notify_pipeline_failure(
                    db,
                    run["source"],
                    rh.detail if rh else "",
                    rh.run_at if rh else datetime.now(timezone.utc),
                )
    except Exception:  # noqa: BLE001
        logger.exception("post-run notifications failed", extra={"service": "worker", "action": "telegram.notify"})


def run_once() -> dict:
    _heartbeat()
    db = SessionLocal()
    try:
        summary = run_pipeline(db)
        logger.info(
            "pipeline run complete",
            extra={"service": "worker", "action": "pipeline.run", "status": "ok"},
        )
        _post_run_notifications(db, summary)
        return summary
    except Exception:
        logger.exception(
            "pipeline run failed",
            extra={"service": "worker", "action": "pipeline.run", "status": "error"},
        )
        raise
    finally:
        db.close()


def sync_sheets_once() -> None:
    if not (settings.SHEETS_SYNC_ENABLED and is_configured()):
        return
    db = SessionLocal()
    try:
        result = sync_all(db)
        logger.info(
            "sheets sync complete",
            extra={"service": "worker", "action": "sheets.sync", "status": result.get("status")},
        )
        if result.get("status") == "failed":
            try:
                from .telegram import notify_sheets_failure

                notify_sheets_failure(db, result)
            except Exception:  # noqa: BLE001
                logger.exception("sheets failure notify failed", extra={"service": "worker"})
    except Exception:
        logger.exception("sheets sync failed", extra={"service": "worker", "action": "sheets.sync"})
    finally:
        db.close()


def _telegram_job(fn_name: str) -> None:
    """Open a session and run a telegram notifier/poller function by name."""
    from . import telegram as tg

    db = SessionLocal()
    try:
        if fn_name == "daily":
            tg.send_daily_summary(db)
        elif fn_name == "evening":
            tg.send_evening_summary(db)
        elif fn_name == "poll":
            tg.poll_once(db)
    except Exception:  # noqa: BLE001
        logger.exception("telegram job failed", extra={"service": "worker", "action": f"telegram.{fn_name}"})
    finally:
        db.close()


def start() -> None:
    _heartbeat()
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_once,
        trigger="interval",
        minutes=settings.SCAN_INTERVAL_MINUTES,
        id="discovery",
        next_run_time=datetime.now(timezone.utc),  # run immediately on boot
        max_instances=1,
        coalesce=True,
    )
    # Scheduled Google Sheets mirror (only runs when enabled + configured).
    scheduler.add_job(
        sync_sheets_once,
        trigger="interval",
        minutes=settings.SHEETS_SYNC_INTERVAL_MINUTES,
        id="sheets_sync",
        max_instances=1,
        coalesce=True,
    )
    # Telegram daily (09:00 IST) + evening (18:00 IST) summaries.
    scheduler.add_job(
        _telegram_job, CronTrigger(hour=9, minute=0, timezone=IST), id="tg_daily", args=["daily"]
    )
    scheduler.add_job(
        _telegram_job, CronTrigger(hour=18, minute=0, timezone=IST), id="tg_evening", args=["evening"]
    )
    # Telegram command poller (read-only commands).
    scheduler.add_job(
        _telegram_job,
        trigger="interval",
        seconds=settings.TELEGRAM_POLL_INTERVAL_SECONDS,
        id="tg_poll",
        args=["poll"],
        max_instances=1,
        coalesce=True,
    )
    # Frequent liveness heartbeat for the Docker health check.
    scheduler.add_job(_heartbeat, trigger="interval", seconds=60, id="heartbeat")
    logger.info(
        f"scheduler started; every {settings.SCAN_INTERVAL_MINUTES}m "
        f"(TEST_MODE={settings.TEST_MODE})",
        extra={"service": "worker", "action": "scheduler.start"},
    )
    scheduler.start()
