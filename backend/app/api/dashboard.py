from datetime import datetime, timedelta, timezone

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
    # "Today" is measured in IST (the user's timezone), not UTC, so the daily
    # boundary doesn't shift ~5.5h. Compare against the IST day's UTC window.
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    day_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    def count(*filters) -> int:
        return db.query(Job).filter(*filters).count()

    new_today = count(Job.discovered_at >= day_start, Job.discovered_at < day_end)

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
