from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..constants import DEFAULT_SKILLS
from ..deps import get_current_user, get_db
from ..models.job import Job, JobScore
from ..models.resume import Resume, ResumeVersion
from ..models.user import User
from ..schemas.dashboard import (
    AnalyticsOverview,
    CountPoint,
    DayPoint,
    ResumeStat,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

_APPLICATIONS_NOTE = (
    "Application/interview metrics are placeholders until the apply engine "
    "(Phase 5) records applications."
)


def _jobs_per_day(db: Session, since) -> list[DayPoint]:
    rows = (
        db.query(func.date(Job.discovered_at).label("d"), func.count().label("c"))
        .filter(Job.discovered_at >= since)
        .group_by("d")
        .order_by("d")
        .all()
    )
    return [DayPoint(day=str(r.d), count=r.c) for r in rows]


def _top(db: Session, column, limit: int) -> list[CountPoint]:
    rows = (
        db.query(column.label("label"), func.count().label("c"))
        .filter(column.isnot(None))
        .group_by(column)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [CountPoint(label=str(r.label), count=r.c) for r in rows]


def _candidate_skills(db: Session) -> list[str]:
    skills: set[str] = set(DEFAULT_SKILLS)
    for r in db.query(ResumeVersion).filter(ResumeVersion.is_current.is_(True)).all():
        for s in r.skills_detected or []:
            if isinstance(s, str):
                skills.add(s.lower())
    return sorted(skills)


def _top_skills(db: Session, limit: int) -> list[CountPoint]:
    """Approximate: count how often each known skill appears in job descriptions."""
    out: list[CountPoint] = []
    for skill in _candidate_skills(db):
        c = db.query(Job).filter(Job.description.ilike(f"%{skill}%")).count()
        if c:
            out.append(CountPoint(label=skill, count=c))
    out.sort(key=lambda x: x.count, reverse=True)
    return out[:limit]


def _resume_stats(db: Session) -> list[ResumeStat]:
    stats: list[ResumeStat] = []
    for resume in db.query(Resume).order_by(Resume.category).all():
        matched = (
            db.query(JobScore)
            .filter(JobScore.matched_resume_category == resume.category)
            .count()
        )
        # applied/interviews come from the applications table in a later phase.
        stats.append(ResumeStat(category=resume.category, matched_jobs=matched))
    return stats


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
    top_n: int = Query(10, ge=1, le=50),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return AnalyticsOverview(
        jobs_per_day=_jobs_per_day(db, since),
        applications_per_day=[],  # populated in Phase 5
        top_companies=_top(db, Job.company, top_n),
        top_locations=_top(db, Job.location, top_n),
        top_skills=_top_skills(db, top_n),
        resume_stats=_resume_stats(db),
        interview_conversion_rate=0.0,  # populated in Phase 5
        note=_APPLICATIONS_NOTE,
    )
