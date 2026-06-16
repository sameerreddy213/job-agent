from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..constants import CLASS_AUTO
from ..deps import get_current_user, get_db
from ..models.job import Job, JobScore, RunHealth
from ..models.user import User
from ..schemas.dashboard import DashboardSummary
from ..schemas.source import RunHealthOut
from ..workflow import State

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()

    def count(*filters) -> int:
        return db.query(Job).filter(*filters).count()

    new_today = db.query(Job).filter(func.date(Job.discovered_at) == today).count()

    # Auto-approve eligible = jobs in REVIEW_QUEUE whose score classed as AUTO.
    auto_eligible = (
        db.query(func.count(Job.id))
        .join(JobScore)
        .filter(Job.archived.is_(False), Job.status == State.REVIEW_QUEUE, JobScore.classification == CLASS_AUTO)
        .scalar()
        or 0
    )

    rows = db.query(RunHealth).order_by(RunHealth.run_at.desc()).all()
    latest: dict[str, RunHealth] = {}
    for r in rows:
        latest.setdefault(r.source, r)
    last_run = rows[0].run_at if rows else None

    return DashboardSummary(
        total_jobs=count(),
        new_today=new_today,
        auto_eligible=auto_eligible,
        review_queue=count(Job.archived.is_(False), Job.status == State.REVIEW_QUEUE),
        rejected=count(Job.status.in_([State.REJECTED, State.FILTERED])),
        archived=count(Job.status == State.ARCHIVED),
        last_run=last_run,
        sources=[RunHealthOut.model_validate(r) for r in latest.values()],
    )
