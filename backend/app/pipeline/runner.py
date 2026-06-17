"""Pipeline orchestrator: discover -> normalize -> dedupe -> filter -> score -> persist.

Records per-source run_health (last_run, jobs_found, errors, response_time, status).
"""
import time

from sqlalchemy.orm import Session

from ..config import settings
from ..connectors import CONNECTOR_REGISTRY
from ..connectors.base import BaseConnector
from ..connectors.sample import SampleConnector
from ..constants import CLASS_REJECT, DEFAULT_SKILLS, first_email
from ..intelligence.matching import ResumeProfile, recommend_resume
from ..models.blacklist import CompanyBlacklist, KeywordBlacklist
from ..models.job import Job, JobScore, RunHealth
from ..models.resume import ResumeVersion
from ..models.source import Source
from ..workflow import State, transition
from .fingerprint import fingerprint
from .filters import Blacklists, filter_job
from .scoring import score_job

STATUS_HEALTHY = "HEALTHY"
STATUS_WARNING = "WARNING"
STATUS_FAILED = "FAILED"


def load_candidate_skills(db: Session) -> list[str]:
    """Aggregate skills from current resume versions; fall back to defaults."""
    rows = db.query(ResumeVersion).filter(ResumeVersion.is_current.is_(True)).all()
    skills: set[str] = set()
    for r in rows:
        for s in r.skills_detected or []:
            if isinstance(s, str):
                skills.add(s.lower())
    return sorted(skills) if skills else list(DEFAULT_SKILLS)


def load_resume_profiles(db: Session) -> list[ResumeProfile]:
    """Build resume profiles (category + detected skills) from current versions."""
    profiles: list[ResumeProfile] = []
    for r in db.query(ResumeVersion).filter(ResumeVersion.is_current.is_(True)).all():
        skills = {s.lower() for s in (r.skills_detected or []) if isinstance(s, str)}
        profiles.append(ResumeProfile(category=r.role_category, skills=skills))
    return profiles


def load_blacklists(db: Session) -> Blacklists:
    companies = {
        c.company.lower() for c in db.query(CompanyBlacklist).all()
    }
    keywords = [
        (k.keyword.lower(), k.applies_to) for k in db.query(KeywordBlacklist).all()
    ]
    return Blacklists(companies=companies, keywords=keywords)


def _build_runs(db: Session) -> list[tuple[BaseConnector, str, Source | None]]:
    """Return (connector, source_label, source_row) tuples to execute."""
    if settings.TEST_MODE:
        return [(SampleConnector(), "sample", None)]

    runs: list[tuple[BaseConnector, str, Source | None]] = []
    for src in db.query(Source).filter(Source.enabled.is_(True)).all():
        cls = CONNECTOR_REGISTRY.get(src.name)
        if cls is None:
            continue
        runs.append((cls(src.config), src.name, src))
    return runs


def run_pipeline(db: Session) -> dict:
    candidate_skills = load_candidate_skills(db)
    blacklists = load_blacklists(db)
    resume_profiles = load_resume_profiles(db)
    summaries: list[dict] = []

    for connector, label, src_row in _build_runs(db):
        start = time.monotonic()
        errors = 0
        detail = ""
        jobs = []
        try:
            jobs = connector.collect()
        except Exception as e:  # noqa: BLE001
            errors = 1
            detail = str(e)[:500]

        elapsed_ms = int((time.monotonic() - start) * 1000)
        new_jobs = 0
        filtered_count = 0
        scored_count = 0

        for nj in jobs:
            fp = fingerprint(nj.company, nj.title, nj.location)
            if db.query(Job.id).filter(Job.fingerprint == fp).first():
                continue  # duplicate — never processed twice

            job = Job(
                source=nj.source,
                external_id=nj.job_id,
                fingerprint=fp,
                company=nj.company,
                title=nj.title,
                location=nj.location,
                description=nj.description,
                experience=nj.experience,
                apply_url=nj.apply_url,
                contact_email=(nj.raw or {}).get("contact_email")
                or first_email(nj.description, nj.title),
                posted_date=nj.posted_date,
                employment_type=nj.employment_type,
                remote_status=nj.remote_status,
                raw=nj.raw or {},
            )
            db.add(job)
            db.flush()  # assign job.id

            passed, reason = filter_job(nj, blacklists)
            if not passed:
                filtered_count += 1
                db.add(
                    JobScore(
                        job_id=job.id,
                        classification="REJECT",
                        passed_filters=False,
                        reasoning=reason,
                    )
                )
                transition(db, job, State.FILTERED, actor="system", reason=reason, commit=False)
            else:
                scored_count += 1
                result = score_job(nj, candidate_skills)
                rec = recommend_resume(nj.title, nj.description, resume_profiles)
                db.add(
                    JobScore(
                        job_id=job.id,
                        freshers_score=result.freshers_score,
                        skills_score=result.skills_score,
                        location_score=result.location_score,
                        role_score=result.role_score,
                        total_score=result.total_score,
                        classification=result.classification,
                        matched_resume_category=rec.selected_category or result.matched_resume_category,
                        reasoning=result.reasoning,
                        passed_filters=True,
                        resume_match_score=rec.match_score,
                        resume_confidence=rec.confidence,
                        matched_skills=rec.matched_skills,
                        missing_skills=rec.missing_skills,
                        resume_reasoning=rec.reasoning,
                    )
                )
                transition(db, job, State.SCORED, actor="system", reason="scored", commit=False)
                if result.classification == CLASS_REJECT:
                    transition(db, job, State.REJECTED, actor="system", reason="below review threshold", commit=False)
                else:
                    transition(db, job, State.REVIEW_QUEUE, actor="system", reason=result.classification, commit=False)
            new_jobs += 1

        if errors:
            status = STATUS_FAILED
        elif len(jobs) < settings.HEALTH_MIN_JOBS_WARNING:
            status = STATUS_WARNING
        else:
            status = STATUS_HEALTHY

        health = RunHealth(
            source=label,
            jobs_found=len(jobs),
            new_jobs=new_jobs,
            filtered=filtered_count,
            scored=scored_count,
            errors=errors,
            response_time_ms=elapsed_ms,
            status=status,
            detail=detail or None,
        )
        db.add(health)

        if src_row is not None:
            from sqlalchemy import func as _f

            src_row.last_run = _f.now()
            src_row.last_status = status
            src_row.last_error = detail or None

        db.commit()
        summaries.append(
            {
                "source": label,
                "jobs_found": len(jobs),
                "new_jobs": new_jobs,
                "errors": errors,
                "response_time_ms": elapsed_ms,
                "status": status,
            }
        )

    return {"test_mode": settings.TEST_MODE, "runs": summaries}
