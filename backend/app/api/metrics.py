from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..deps import get_db
from ..metrics import compute_metrics, render_prometheus

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Session = Depends(get_db)) -> str:
    """Prometheus exposition format. Public (no PII), like /health."""
    return render_prometheus(compute_metrics(db))


@router.get("/metrics.json")
def metrics_json(db: Session = Depends(get_db)) -> dict:
    return compute_metrics(db)
