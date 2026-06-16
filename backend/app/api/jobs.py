import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..constants import ALLOWED_CATEGORIES
from ..deps import get_current_user, get_db
from ..intelligence import extract_skills, recommend_resume
from ..intelligence.matching import ResumeProfile
from ..models.job import Job, JobScore
from ..models.resume import ResumeVersion
from ..models.user import User
from ..models.workflow import JobStateHistory
from ..schemas.job import JobDetailOut, JobOut, JobStateHistoryOut
from ..applications import provision_for_job
from ..workflow import InvalidTransition, State, snooze as snooze_job, transition

router = APIRouter(prefix="/jobs", tags=["jobs"])


class ResumeOverride(BaseModel):
    category: str


class ReasonBody(BaseModel):
    reason: str | None = None


class SnoozeBody(BaseModel):
    hours: int = 24
    reason: str | None = None


class BulkBody(BaseModel):
    ids: list[uuid.UUID]
    reason: str | None = None


def _transition_or_400(db: Session, job: Job, new_state: str, actor: str, reason: str | None):
    try:
        transition(db, job, new_state, actor=actor, reason=reason)
    except InvalidTransition as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))


def _resume_profiles(db: Session) -> list[ResumeProfile]:
    profiles: list[ResumeProfile] = []
    for r in db.query(ResumeVersion).filter(ResumeVersion.is_current.is_(True)).all():
        skills = {s.lower() for s in (r.skills_detected or []) if isinstance(s, str)}
        profiles.append(ResumeProfile(category=r.role_category, skills=skills))
    return profiles


@router.get("", response_model=list[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    status_filter: str | None = Query(None, alias="status"),
    source: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    archived: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = db.query(Job).filter(Job.archived.is_(archived))
    if status_filter:
        q = q.filter(Job.status == status_filter)
    if source:
        q = q.filter(Job.source == source)
    if min_score is not None:
        q = q.join(JobScore).filter(JobScore.total_score >= min_score)
    # Newest first; scored jobs still ordered by discovery for stable paging.
    q = q.order_by(Job.discovered_at.desc())
    return q.offset(offset).limit(limit).all()


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post("/{job_id}/resume", response_model=JobDetailOut)
def override_resume(
    job_id: uuid.UUID,
    body: ResumeOverride,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually select a resume for a job (Resume Override Support, Phase 5A)."""
    if body.category not in ALLOWED_CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown category '{body.category}'")
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.score is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Job has not been scored")

    # Recompute matched/missing skills against the chosen resume's skills.
    version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.role_category == body.category, ResumeVersion.is_current.is_(True))
        .first()
    )
    resume_skills = {s.lower() for s in (version.skills_detected if version else [])}
    job_skills = set(extract_skills(f"{job.title} {job.description or ''}"))
    matched = sorted(job_skills & resume_skills)
    missing = sorted(job_skills - resume_skills)
    coverage = round(len(matched) / len(job_skills) * 100) if job_skills else 0

    score = job.score
    score.matched_resume_category = body.category
    score.matched_skills = matched
    score.missing_skills = missing
    score.resume_match_score = coverage
    score.resume_confidence = 100  # manual selection is authoritative
    score.resume_reasoning = f"Manually overridden to '{body.category}'."
    score.resume_override = True
    db.commit()
    db.refresh(job)
    write_audit(db, user.username, "job.resume_override", "job", job_id, {"category": body.category})
    return job


@router.post("/{job_id}/rematch", response_model=JobDetailOut)
def rematch_resume(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run the resume recommendation for a job using current resumes."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.score is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Job has not been scored")

    rec = recommend_resume(job.title, job.description, _resume_profiles(db))
    score = job.score
    if rec.selected_category:
        score.matched_resume_category = rec.selected_category
    score.matched_skills = rec.matched_skills
    score.missing_skills = rec.missing_skills
    score.resume_match_score = rec.match_score
    score.resume_confidence = rec.confidence
    score.resume_reasoning = rec.reasoning
    score.resume_override = False
    db.commit()
    db.refresh(job)
    write_audit(db, user.username, "job.rematch", "job", job_id)
    return job


# --------------------------------------------------------------------------- #
# Workflow actions (Phase 7A)
# --------------------------------------------------------------------------- #
# NOTE: Bulk routes (/bulk/*) are declared BEFORE the parametric /{job_id}/*
# routes. FastAPI matches routes in registration order and `{job_id}` uses the
# default string path matcher, so "/jobs/bulk/approve" would otherwise match
# "/jobs/{job_id}/approve" (job_id="bulk") and 422 on UUID validation.
def _bulk(db: Session, ids: list[uuid.UUID], new_state: str, actor: str, reason: str | None) -> dict:
    results = []
    for jid in ids:
        job = db.get(Job, jid)
        if job is None:
            results.append({"id": str(jid), "ok": False, "error": "not found"})
            continue
        try:
            transition(db, job, new_state, actor=actor, reason=reason, commit=False)
            results.append({"id": str(jid), "ok": True})
        except InvalidTransition as e:
            results.append({"id": str(jid), "ok": False, "error": str(e)})
    db.commit()
    ok = sum(1 for r in results if r["ok"])
    return {"requested": len(ids), "succeeded": ok, "failed": len(ids) - ok, "results": results}


@router.post("/bulk/approve")
def bulk_approve(body: BulkBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return _bulk(db, body.ids, State.APPROVED, user.username, body.reason or "bulk approve")


@router.post("/bulk/reject")
def bulk_reject(body: BulkBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return _bulk(db, body.ids, State.REJECTED, user.username, body.reason or "bulk reject")


@router.post("/bulk/archive")
def bulk_archive(body: BulkBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return _bulk(db, body.ids, State.ARCHIVED, user.username, body.reason or "bulk archive")


def _get_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post("/{job_id}/approve", response_model=JobDetailOut)
def approve(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_job(db, job_id)
    _transition_or_400(db, job, State.APPROVED, user.username, "approved")
    # Phase 8A: provision an application (generate materials + move to READY).
    # Best-effort — a provisioning hiccup must not fail the approval itself.
    try:
        provision_for_job(db, job, actor=user.username)
    except Exception:  # noqa: BLE001 - provisioning is non-critical to approval
        db.rollback()
    db.refresh(job)
    return job


@router.post("/{job_id}/reject", response_model=JobDetailOut)
def reject(job_id: uuid.UUID, body: ReasonBody | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_job(db, job_id)
    _transition_or_400(db, job, State.REJECTED, user.username, (body.reason if body else None) or "rejected")
    db.refresh(job)
    return job


@router.post("/{job_id}/archive", response_model=JobDetailOut)
def archive(job_id: uuid.UUID, body: ReasonBody | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_job(db, job_id)
    _transition_or_400(db, job, State.ARCHIVED, user.username, (body.reason if body else None) or "archived")
    db.refresh(job)
    return job


@router.post("/{job_id}/snooze", response_model=JobDetailOut)
def snooze(job_id: uuid.UUID, body: SnoozeBody | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_job(db, job_id)
    hours = body.hours if body else 24
    until = datetime.now(timezone.utc) + timedelta(hours=hours)
    snooze_job(db, job, until, actor=user.username, reason=(body.reason if body else None) or f"snoozed {hours}h")
    db.refresh(job)
    return job


@router.get("/{job_id}/workflow/history", response_model=list[JobStateHistoryOut])
def workflow_history(job_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_job(db, job_id)
    return (
        db.query(JobStateHistory)
        .filter(JobStateHistory.job_id == job_id)
        .order_by(JobStateHistory.created_at.asc())
        .all()
    )
