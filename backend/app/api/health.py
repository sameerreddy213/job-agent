from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.job import RunHealth
from ..models.user import User
from ..schemas.source import RunHealthOut

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": 8}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "up"}


@router.get("/health/sources", response_model=list[RunHealthOut])
def health_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Latest run health per source (HEALTHY / WARNING / FAILED)."""
    rows = db.query(RunHealth).order_by(RunHealth.run_at.desc()).all()
    latest: dict[str, RunHealth] = {}
    for r in rows:
        latest.setdefault(r.source, r)
    return list(latest.values())
