"""Application lifecycle state machine and provisioning service (Phase 8A).

Tracks applications only. NOTHING here submits an application, drives a browser,
or uses Playwright. Submission stays a manual, human action; SUBMITTED merely
*records* that the user submitted it elsewhere.
"""
from datetime import datetime, timezone

from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from .ats import AtsType, detect_ats
from .audit import write_audit
from .materials import GenerationError, generate_materials
from .models.application import Application, ApplicationAnswer, ApplicationDocument, ApplicationEvent
from .models.job import Job
from .models.material import Material


def readiness_counts(db: Session) -> dict:
    """Aggregate readiness/ATS counts in SQL (no per-row Python loop).

    Mirrors ats.evaluate_readiness: an application is "ready" when it has
    documents + a resume + answers AND needs no manual fields. Used by /metrics
    and the ATS breakdown, which are hit frequently."""
    total = db.query(func.count(Application.id)).scalar() or 0
    by_ats = dict(
        db.query(Application.ats_type, func.count(Application.id)).group_by(Application.ats_type).all()
    )
    ats_unknown = by_ats.get(AtsType.UNKNOWN, 0)
    manual = (
        db.query(func.count(Application.id))
        .filter(Application.requires_manual_fields.is_(True))
        .scalar()
        or 0
    )
    has_docs = exists().where(ApplicationDocument.application_id == Application.id)
    has_answers = exists().where(ApplicationAnswer.application_id == Application.id)
    ready = (
        db.query(func.count(Application.id))
        .filter(
            Application.requires_manual_fields.is_(False),
            Application.resume_category.isnot(None),
            Application.resume_category != "",
            has_docs,
            has_answers,
        )
        .scalar()
        or 0
    )
    return {
        "total": total,
        "ats_detected": total - ats_unknown,
        "ats_unknown": ats_unknown,
        "ready_to_apply": ready,
        "manual_review_required": manual,
        "by_ats": by_ats,
    }


class AppState:
    NOT_STARTED = "NOT_STARTED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    INTERVIEW = "INTERVIEW"
    ASSESSMENT = "ASSESSMENT"
    REJECTED = "REJECTED"
    OFFER = "OFFER"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"


ALL_APP_STATES = {
    AppState.NOT_STARTED, AppState.READY, AppState.IN_PROGRESS, AppState.SUBMITTED,
    AppState.INTERVIEW, AppState.ASSESSMENT, AppState.REJECTED, AppState.OFFER,
    AppState.ACCEPTED, AppState.WITHDRAWN,
}

# WITHDRAWN is reachable from every non-terminal state.
VALID_APP_TRANSITIONS: dict[str, set[str]] = {
    AppState.NOT_STARTED: {AppState.READY, AppState.IN_PROGRESS, AppState.WITHDRAWN},
    AppState.READY: {AppState.IN_PROGRESS, AppState.SUBMITTED, AppState.WITHDRAWN},
    AppState.IN_PROGRESS: {AppState.SUBMITTED, AppState.WITHDRAWN},
    AppState.SUBMITTED: {AppState.INTERVIEW, AppState.ASSESSMENT, AppState.REJECTED, AppState.OFFER, AppState.WITHDRAWN},
    AppState.INTERVIEW: {AppState.ASSESSMENT, AppState.OFFER, AppState.REJECTED, AppState.WITHDRAWN},
    AppState.ASSESSMENT: {AppState.INTERVIEW, AppState.OFFER, AppState.REJECTED, AppState.WITHDRAWN},
    AppState.OFFER: {AppState.ACCEPTED, AppState.REJECTED, AppState.WITHDRAWN},
    AppState.REJECTED: set(),
    AppState.ACCEPTED: set(),
    AppState.WITHDRAWN: set(),
}


class InvalidAppTransition(Exception):
    pass


def can_transition(current: str, new: str) -> bool:
    return new in VALID_APP_TRANSITIONS.get(current, set())


def _record(db: Session, app: Application, previous: str | None, new: str, actor: str, reason: str | None):
    db.add(
        ApplicationEvent(
            application_id=app.id, previous_state=previous, new_state=new, actor=actor, reason=reason
        )
    )
    write_audit(
        db, actor, "application.transition", "application", app.id,
        {"from": previous, "to": new, "reason": reason}, commit=False,
    )


def transition(
    db: Session, app: Application, new_state: str, actor: str, reason: str | None = None, commit: bool = True
) -> None:
    if new_state not in ALL_APP_STATES:
        raise InvalidAppTransition(f"Unknown application state '{new_state}'")
    current = app.status
    if not can_transition(current, new_state):
        raise InvalidAppTransition(f"Illegal application transition {current} -> {new_state}")

    _record(db, app, current, new_state, actor, reason)
    app.status = new_state
    if new_state == AppState.SUBMITTED and app.submitted_at is None:
        app.submitted_at = datetime.now(timezone.utc)
    if commit:
        db.commit()


def _sync_documents(db: Session, app: Application, material: Material) -> None:
    """Replace the application's documents with rows reflecting the material's
    current exports, and refresh its answers."""
    for doc in list(app.documents):
        db.delete(doc)
    for ans in list(app.answers):
        db.delete(ans)
    db.flush()

    exports = [("packet", "txt", material.txt_path), ("packet", "docx", material.docx_path),
               ("packet", "pdf", material.pdf_path)]
    for kind, fmt, path in exports:
        if path:
            db.add(ApplicationDocument(
                application_id=app.id, material_id=material.id, kind=kind, fmt=fmt, path=path
            ))
    for qa in material.application_answers or []:
        if isinstance(qa, dict):
            db.add(ApplicationAnswer(
                application_id=app.id, question=qa.get("question", ""), answer=qa.get("answer")
            ))


def apply_ats_detection(app: Application, job: Job) -> None:
    """Detect and store the ATS target for an application (idempotent)."""
    det = detect_ats(job.apply_url, source=job.source)
    app.ats_type = det.ats_type
    app.ats_version = det.ats_version
    app.application_url = det.application_url
    app.supports_easy_apply = det.supports_easy_apply
    app.requires_manual_fields = det.requires_manual_fields


def get_or_create(db: Session, job: Job, actor: str) -> Application:
    app = db.query(Application).filter(Application.job_id == job.id).first()
    if app is None:
        app = Application(job_id=job.id, status=AppState.NOT_STARTED)
        apply_ats_detection(app, job)
        db.add(app)
        db.flush()
        _record(db, app, None, AppState.NOT_STARTED, actor, "application created")
    else:
        apply_ats_detection(app, job)  # refresh in case apply_url changed
    return app


def provision_for_job(db: Session, job: Job, actor: str, commit: bool = True) -> Application:
    """On job approval: ensure an application exists, generate materials, link the
    documents/answers, and move the application to READY.

    If materials cannot be generated yet (e.g. profile not set), the application
    is created and left at NOT_STARTED with an event explaining why — it is never
    silently advanced to READY without materials.
    """
    app = get_or_create(db, job, actor)
    try:
        material = generate_materials(db, job)
    except GenerationError as e:
        _record(db, app, app.status, app.status, actor, f"materials pending: {e}")
        if commit:
            db.commit()
        return app

    app.material_id = material.id
    app.resume_category = material.resume_category
    _sync_documents(db, app, material)
    if can_transition(app.status, AppState.READY):
        transition(db, app, AppState.READY, actor=actor, reason="materials generated", commit=False)
    if commit:
        db.commit()
        db.refresh(app)
    return app
