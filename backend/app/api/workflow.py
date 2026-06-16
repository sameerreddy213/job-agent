from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.job import Job
from ..models.user import User
from ..models.workflow import JobStateHistory
from ..schemas.job import JobOut
from ..schemas.workflow import (
    ApprovalStats,
    DayCount,
    StatePoint,
    TimelineEvent,
    WorkflowAnalytics,
)
from ..workflow import ALL_STATES, State

router = APIRouter(prefix="/workflow", tags=["workflow"])

# A snooze is recorded as a history row whose previous and new state are equal
# (the job stays put but the action is audited). Used to separate snoozes from
# genuine state changes in the analytics.
_DECISION_STATES = {State.APPROVED, State.REJECTED, State.ARCHIVED}


@router.get("/state-counts")
def state_counts(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    rows = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    counts = {state: 0 for state in ALL_STATES}
    for state, n in rows:
        counts[state] = n
    return counts


@router.get("/pending-review", response_model=list[JobOut])
def pending_review(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Jobs awaiting a decision (REVIEW_QUEUE), newest first."""
    return (
        db.query(Job)
        .filter(Job.status == State.REVIEW_QUEUE, Job.archived.is_(False))
        .order_by(Job.discovered_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/timeline", response_model=list[TimelineEvent])
def timeline(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    job_id: str | None = Query(None, description="Restrict to a single job"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Workflow transition feed, joined with job company/title.

    With `job_id` it is the full timeline for one job (oldest first); without it,
    a global feed of recent transitions across all jobs (newest first).
    """
    q = (
        db.query(
            JobStateHistory.id,
            JobStateHistory.job_id,
            Job.company,
            Job.title,
            JobStateHistory.previous_state,
            JobStateHistory.new_state,
            JobStateHistory.actor,
            JobStateHistory.reason,
            JobStateHistory.created_at,
        )
        .join(Job, Job.id == JobStateHistory.job_id)
    )
    if job_id:
        q = q.filter(JobStateHistory.job_id == job_id).order_by(JobStateHistory.created_at.asc())
    else:
        q = q.order_by(JobStateHistory.created_at.desc())
    rows = q.offset(offset).limit(limit).all()
    return [
        TimelineEvent(
            id=r.id, job_id=r.job_id, company=r.company, title=r.title,
            previous_state=r.previous_state, new_state=r.new_state,
            actor=r.actor, reason=r.reason, created_at=r.created_at,
        )
        for r in rows
    ]


def _avg_review_seconds(db: Session, since: datetime) -> float | None:
    """Mean time from a job entering REVIEW_QUEUE to its first decision.

    Computed in Python over the (small) set of decision-bearing history rows so
    the logic stays portable across SQLite (tests) and Postgres (prod).
    """
    # Last time each job entered REVIEW_QUEUE.
    entered: dict = {}
    for jid, ts in (
        db.query(JobStateHistory.job_id, JobStateHistory.created_at)
        .filter(JobStateHistory.new_state == State.REVIEW_QUEUE)
        .order_by(JobStateHistory.created_at.asc())
        .all()
    ):
        entered[jid] = ts  # later rows overwrite -> most recent entry kept

    durations: list[float] = []
    for jid, entry_ts in entered.items():
        decision = (
            db.query(JobStateHistory.created_at)
            .filter(
                JobStateHistory.job_id == jid,
                JobStateHistory.new_state.in_(_DECISION_STATES),
                JobStateHistory.previous_state != JobStateHistory.new_state,
                JobStateHistory.created_at >= entry_ts,
            )
            .order_by(JobStateHistory.created_at.asc())
            .first()
        )
        if decision and decision[0] >= since:
            durations.append((decision[0] - entry_ts).total_seconds())
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


def _per_day(db: Session, new_state: str, since: datetime, *, snooze: bool | None = None) -> list[DayCount]:
    q = db.query(
        func.date(JobStateHistory.created_at).label("d"), func.count().label("c")
    ).filter(JobStateHistory.new_state == new_state, JobStateHistory.created_at >= since)
    if snooze is True:
        q = q.filter(JobStateHistory.previous_state == JobStateHistory.new_state)
    elif snooze is False:
        q = q.filter(JobStateHistory.previous_state != JobStateHistory.new_state)
    rows = q.group_by("d").order_by("d").all()
    return [DayCount(day=str(r.d), count=r.c) for r in rows]


def _count(db: Session, since: datetime, new_state: str, *, snooze: bool | None = None) -> int:
    q = db.query(func.count(JobStateHistory.id)).filter(
        JobStateHistory.new_state == new_state, JobStateHistory.created_at >= since
    )
    if snooze is True:
        q = q.filter(JobStateHistory.previous_state == JobStateHistory.new_state)
    elif snooze is False:
        q = q.filter(JobStateHistory.previous_state != JobStateHistory.new_state)
    return q.scalar() or 0


@router.get("/analytics", response_model=WorkflowAnalytics)
def analytics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    state_rows = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    by_state = defaultdict(int, {s: n for s, n in state_rows})
    jobs_by_state = [StatePoint(state=s, count=by_state[s]) for s in sorted(ALL_STATES)]

    total_transitions = (
        db.query(func.count(JobStateHistory.id))
        .filter(JobStateHistory.created_at >= since)
        .scalar()
        or 0
    )
    approvals = _count(db, since, State.APPROVED, snooze=False)
    rejections = _count(db, since, State.REJECTED, snooze=False)
    archives = _count(db, since, State.ARCHIVED, snooze=False)
    # Snoozes: any state with previous == new.
    snoozes = (
        db.query(func.count(JobStateHistory.id))
        .filter(
            JobStateHistory.created_at >= since,
            JobStateHistory.previous_state == JobStateHistory.new_state,
        )
        .scalar()
        or 0
    )
    decisions = approvals + rejections + snoozes
    pct = lambda n: round(n / decisions * 100, 1) if decisions else 0.0  # noqa: E731

    return WorkflowAnalytics(
        days=days,
        jobs_by_state=jobs_by_state,
        total_transitions=total_transitions,
        approvals=approvals,
        rejections=rejections,
        snoozes=snoozes,
        archives=archives,
        decisions=decisions,
        approval_pct=pct(approvals),
        rejection_pct=pct(rejections),
        snooze_pct=pct(snoozes),
        avg_review_seconds=_avg_review_seconds(db, since),
        pending_review_trend=_per_day(db, State.REVIEW_QUEUE, since),
    )


@router.get("/approval-stats", response_model=ApprovalStats)
def approval_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    approved = _count(db, since, State.APPROVED, snooze=False)
    rejected = _count(db, since, State.REJECTED, snooze=False)
    archived = _count(db, since, State.ARCHIVED, snooze=False)
    snoozed = (
        db.query(func.count(JobStateHistory.id))
        .filter(
            JobStateHistory.created_at >= since,
            JobStateHistory.previous_state == JobStateHistory.new_state,
        )
        .scalar()
        or 0
    )
    decided = approved + rejected
    return ApprovalStats(
        days=days,
        approved=approved,
        rejected=rejected,
        archived=archived,
        snoozed=snoozed,
        approval_rate=round(approved / decided * 100, 1) if decided else 0.0,
        rejection_rate=round(rejected / decided * 100, 1) if decided else 0.0,
        approved_per_day=_per_day(db, State.APPROVED, since, snooze=False),
        rejected_per_day=_per_day(db, State.REJECTED, since, snooze=False),
    )
