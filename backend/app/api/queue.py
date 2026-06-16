from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..constants import CLASS_AUTO, CLASS_REVIEW
from ..deps import get_current_user, get_db
from ..models.job import Job, JobScore
from ..models.user import User
from ..schemas.job import JobOut
from ..workflow import State

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=list[JobOut])
def review_queue(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    classification: str | None = Query(None, description="AUTO_APPROVE_ELIGIBLE or REVIEW_QUEUE (score class)"),
    source: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Actionable jobs: those in the REVIEW_QUEUE workflow state, highest score first.

    The `classification` filter narrows by the score's classification (auto-eligible
    vs review) stored on JobScore.
    """
    q = (
        db.query(Job)
        .join(JobScore)
        .filter(Job.archived.is_(False), Job.status == State.REVIEW_QUEUE)
    )
    if classification:
        q = q.filter(JobScore.classification == classification)
    if source:
        q = q.filter(Job.source == source)
    if min_score is not None:
        q = q.filter(JobScore.total_score >= min_score)
    q = q.order_by(JobScore.total_score.desc(), Job.discovered_at.desc())
    return q.offset(offset).limit(limit).all()


@router.get("/counts")
def queue_counts(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    base = db.query(func.count(Job.id)).join(JobScore).filter(
        Job.archived.is_(False), Job.status == State.REVIEW_QUEUE
    )
    return {
        "auto_eligible": base.filter(JobScore.classification == CLASS_AUTO).scalar() or 0,
        "review_queue": base.filter(JobScore.classification == CLASS_REVIEW).scalar() or 0,
    }
