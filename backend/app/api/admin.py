from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings
from ..deps import get_current_user, get_db
from ..models.sync import SheetSyncRun
from ..models.user import User
from ..pipeline.runner import run_pipeline
from ..sheets import is_configured, sync_all

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run-now")
def run_now(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Manually trigger one discovery pipeline run (synchronous)."""
    result = run_pipeline(db)
    write_audit(db, user.username, "pipeline.run_now", "pipeline", payload=result)
    return result


@router.post("/sync-sheets")
def sync_sheets(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Manually trigger a one-way Google Sheets mirror sync."""
    result = sync_all(db)
    write_audit(db, user.username, "sheets.sync", "sheets", payload=result)
    return result


@router.get("/sync-sheets/status")
def sync_status(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    last = db.query(SheetSyncRun).order_by(SheetSyncRun.run_at.desc()).first()
    return {
        "configured": is_configured(),
        "enabled": settings.SHEETS_SYNC_ENABLED,
        "interval_minutes": settings.SHEETS_SYNC_INTERVAL_MINUTES,
        "last_sync_at": last.run_at.isoformat() if last else None,
        "last_status": last.status if last else None,
        "rows_written": last.rows_written if last else 0,
        "duration_ms": last.duration_ms if last else 0,
        "error": last.error if last else None,
        "tabs": last.tabs if last else {},
    }
