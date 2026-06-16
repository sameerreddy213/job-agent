import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..applications import (
    ALL_APP_STATES,
    AppState,
    InvalidAppTransition,
    apply_ats_detection,
    get_or_create,
    transition,
)
from ..applications import provision_for_job, readiness_counts
from ..ats import AtsDetection, AtsType, evaluate_readiness
from ..audit import write_audit
from ..deps import get_current_user, get_db
from ..models.application import Application, ApplicationEvent
from ..models.job import Job
from ..models.material import Material
from ..models.profile import Profile
from ..models.user import User
from ..packet import PacketError, generate_packet
from ..schemas.application import (
    ApplicationAnalytics,
    ApplicationDetailOut,
    ApplicationEventOut,
    ApplicationOut,
    AtsBreakdown,
    AtsCount,
    ChecklistItem,
    ChecklistOut,
    CreateApplicationBody,
    PacketOut,
    ReadinessItem,
    ReadinessReport,
    StateCount,
    TransitionBody,
    UpdateApplicationBody,
)

_PACKET_MEDIA = {
    "txt": ("text/plain", "packet_txt_path", "application-packet.txt"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "packet_docx_path",
        "application-packet.docx",
    ),
    "pdf": ("application/pdf", "packet_pdf_path", "application-packet.pdf"),
}

router = APIRouter(prefix="/applications", tags=["applications"])


def _enrich(db: Session, app: Application) -> ApplicationOut:
    job = db.get(Job, app.job_id)
    out = ApplicationOut.model_validate(app)
    if job:
        out.company = job.company
        out.title = job.title
    return out


def _get(db: Session, app_id: uuid.UUID) -> Application:
    app = (
        db.query(Application)
        .options(
            selectinload(Application.documents),
            selectinload(Application.answers),
            selectinload(Application.events),
        )
        .filter(Application.id == app_id)
        .first()
    )
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    status_filter: str | None = Query(None, alias="status"),
    job_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    q = db.query(Application)
    if status_filter:
        q = q.filter(Application.status == status_filter)
    if job_id:
        q = q.filter(Application.job_id == job_id)
    rows = q.order_by(Application.updated_at.desc()).offset(offset).limit(limit).all()
    return [_enrich(db, a) for a in rows]


@router.post("", response_model=ApplicationDetailOut, status_code=status.HTTP_201_CREATED)
def create_application(
    body: CreateApplicationBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually create (or fetch) an application for a job, then provision it
    (generate materials + move to READY). Idempotent per job."""
    job = db.get(Job, body.job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    app = provision_for_job(db, job, actor=user.username)
    write_audit(db, user.username, "application.create", "application", app.id, {"job_id": str(body.job_id)})
    return _get(db, app.id)


@router.get("/analytics", response_model=ApplicationAnalytics)
def analytics(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total = db.query(func.count(Application.id)).scalar() or 0
    state_rows = db.query(Application.status, func.count(Application.id)).group_by(Application.status).all()
    counts = {s: 0 for s in ALL_APP_STATES}
    for s, n in state_rows:
        counts[s] = n
    by_state = [StateCount(state=s, count=counts[s]) for s in sorted(ALL_APP_STATES)]

    def ev(state: str) -> int:
        return (
            db.query(func.count(func.distinct(ApplicationEvent.application_id)))
            .filter(ApplicationEvent.new_state == state)
            .scalar()
            or 0
        )

    created = total
    submitted = ev(AppState.SUBMITTED)
    interviews = ev(AppState.INTERVIEW)
    assessments = ev(AppState.ASSESSMENT)
    offers = ev(AppState.OFFER)
    rejections = ev(AppState.REJECTED)
    accepted = ev(AppState.ACCEPTED)
    withdrawn = ev(AppState.WITHDRAWN)

    rate = lambda n, d: round(n / d * 100, 1) if d else 0.0  # noqa: E731
    return ApplicationAnalytics(
        total=total,
        by_state=by_state,
        created=created,
        submitted=submitted,
        interviews=interviews,
        assessments=assessments,
        offers=offers,
        rejections=rejections,
        accepted=accepted,
        withdrawn=withdrawn,
        submit_rate=rate(submitted, created),
        interview_rate=rate(interviews, submitted),
        offer_rate=rate(offers, submitted),
        acceptance_rate=rate(accepted, offers),
    )


# --------------------------------------------------------------------------- #
# ATS integration layer / readiness (Phase 8B)
# --------------------------------------------------------------------------- #
def _ats_of(app: Application) -> AtsDetection:
    """Reconstruct an AtsDetection from the application's stored ATS fields."""
    return AtsDetection(
        ats_type=app.ats_type,
        ats_version=app.ats_version,
        application_url=app.application_url,
        supports_easy_apply=app.supports_easy_apply,
        requires_manual_fields=app.requires_manual_fields,
    )


def _readiness(app: Application) -> ReadinessReport:
    report = evaluate_readiness(
        has_documents=len(app.documents) > 0,
        resume_category=app.resume_category,
        answer_count=len(app.answers),
        ats=_ats_of(app),
    )
    return ReadinessReport(application_id=app.id, **report.__dict__)


def _all_with_children(db: Session):
    return (
        db.query(Application)
        .options(selectinload(Application.documents), selectinload(Application.answers))
        .all()
    )


@router.get("/readiness", response_model=list[ReadinessItem])
def readiness_list(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    ready_only: bool = Query(False, description="Only applications that are fully ready"),
):
    items: list[ReadinessItem] = []
    for app in _all_with_children(db):
        r = _readiness(app)
        if ready_only and not r.ready:
            continue
        base = _enrich(db, app)
        items.append(ReadinessItem(
            **base.model_dump(),
            ready_score=r.ready_score,
            ready=r.ready,
            manual_review_required=r.manual_review_required,
        ))
    items.sort(key=lambda i: i.ready_score, reverse=True)
    return items


@router.get("/ready-queue", response_model=list[ReadinessItem])
def ready_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Applications that are fully ready and need no manual fields."""
    return readiness_list(db=db, _=user, ready_only=True)


@router.get("/ats-breakdown", response_model=AtsBreakdown)
def ats_breakdown(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rc = readiness_counts(db)  # aggregated in SQL
    return AtsBreakdown(
        total=rc["total"],
        detected=rc["ats_detected"],
        unknown=rc["ats_unknown"],
        ready_to_apply=rc["ready_to_apply"],
        manual_review_required=rc["manual_review_required"],
        by_ats=[AtsCount(ats_type=k, count=v) for k, v in sorted(rc["by_ats"].items())],
    )


@router.get("/{app_id}/readiness", response_model=ReadinessReport)
def application_readiness(app_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _readiness(_get(db, app_id))


@router.post("/{app_id}/detect-ats", response_model=ApplicationDetailOut)
def redetect_ats(app_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = _get(db, app_id)
    job = db.get(Job, app.job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    apply_ats_detection(app, job)
    db.commit()
    write_audit(db, user.username, "application.detect_ats", "application", app.id, {"ats_type": app.ats_type})
    return _get(db, app_id)


# --------------------------------------------------------------------------- #
# Manual apply assistant (Phase 8C)
# --------------------------------------------------------------------------- #
def _material_for(db: Session, app: Application) -> Material | None:
    return db.query(Material).filter(Material.job_id == app.job_id).first()


def _packet_formats(app: Application) -> list[str]:
    out = []
    for fmt, (_, attr, _f) in _PACKET_MEDIA.items():
        path = getattr(app, attr)
        if path and os.path.exists(path):
            out.append(fmt)
    return out


def _build_checklist(db: Session, app: Application) -> ChecklistOut:
    material = _material_for(db, app)
    profile_exists = db.get(Profile, 1) is not None
    items = [
        ChecklistItem(key="profile", label="Profile complete", done=profile_exists, required=True),
        ChecklistItem(key="resume", label="Resume selected", done=bool(app.resume_category), required=True),
        ChecklistItem(key="materials", label="Materials generated", done=len(app.documents) > 0, required=True),
        ChecklistItem(key="cover_letter", label="Cover letter prepared",
                      done=bool(material and material.cover_letter_text), required=False),
        ChecklistItem(key="answers", label="Application answers prepared", done=len(app.answers) > 0, required=True),
        ChecklistItem(key="apply_url", label="Apply URL known", done=bool(app.application_url), required=False),
        ChecklistItem(key="manual_fields", label="Manual fields reviewed",
                      done=(not app.requires_manual_fields) or app.ready_confirmed, required=False),
        ChecklistItem(key="packet", label="Packet generated", done=app.packet_generated_at is not None, required=True),
        ChecklistItem(key="confirmed", label="Marked ready to apply", done=app.ready_confirmed, required=True),
    ]
    complete = all(i.done for i in items if i.required)
    return ChecklistOut(application_id=app.id, items=items, complete=complete, ready_confirmed=app.ready_confirmed)


@router.get("/{app_id}/checklist", response_model=ChecklistOut)
def checklist(app_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _build_checklist(db, _get(db, app_id))


@router.post("/{app_id}/confirm-ready", response_model=ApplicationDetailOut)
def confirm_ready(app_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Record the user's confirmation that they will apply manually. Does NOT
    submit — it only marks intent and is reflected in metrics."""
    app = _get(db, app_id)
    if not app.ready_confirmed:
        app.ready_confirmed = True
        app.ready_confirmed_at = datetime.now(timezone.utc)
        write_audit(db, user.username, "application.ready_confirmed", "application", app.id, commit=False)
        db.commit()
    return _get(db, app_id)


@router.get("/{app_id}/packet", response_model=PacketOut)
def packet_status(app_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    app = _get(db, app_id)
    return PacketOut(
        application_id=app.id,
        generated=app.packet_generated_at is not None,
        generated_at=app.packet_generated_at,
        formats=_packet_formats(app),
    )


@router.post("/{app_id}/packet", response_model=PacketOut)
def build_packet(app_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = _get(db, app_id)
    material = _material_for(db, app)
    if material is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Generate materials before building a packet")
    job = db.get(Job, app.job_id)
    try:
        generate_packet(db, app, material, job)
    except PacketError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    write_audit(db, user.username, "application.packet_generated", "application", app.id)
    return PacketOut(
        application_id=app.id, generated=True,
        generated_at=app.packet_generated_at, formats=_packet_formats(app),
    )


@router.get("/{app_id}/packet/download/{fmt}")
def download_packet(
    app_id: uuid.UUID,
    fmt: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if fmt not in _PACKET_MEDIA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Format must be txt, docx, or pdf")
    app = _get(db, app_id)
    media_type, attr, filename = _PACKET_MEDIA[fmt]
    path = getattr(app, attr)
    if not path or not os.path.exists(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Packet not generated for this format")
    write_audit(db, user.username, "application.packet_downloaded", "application", app.id, {"fmt": fmt})
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/{app_id}", response_model=ApplicationDetailOut)
def get_application(app_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    app = _get(db, app_id)
    out = ApplicationDetailOut.model_validate(app)
    job = db.get(Job, app.job_id)
    if job:
        out.company = job.company
        out.title = job.title
    out.events = sorted(out.events, key=lambda e: e.created_at)
    return out


@router.patch("/{app_id}", response_model=ApplicationDetailOut)
def update_application(
    app_id: uuid.UUID,
    body: UpdateApplicationBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    app = _get(db, app_id)
    if body.notes is not None:
        app.notes = body.notes
    if body.resume_category is not None:
        app.resume_category = body.resume_category
    db.commit()
    write_audit(db, user.username, "application.update", "application", app.id)
    return _get(db, app_id)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(app_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = _get(db, app_id)
    db.delete(app)
    db.commit()
    write_audit(db, user.username, "application.delete", "application", app_id)


@router.post("/{app_id}/transition", response_model=ApplicationDetailOut)
def transition_application(
    app_id: uuid.UUID,
    body: TransitionBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    app = _get(db, app_id)
    try:
        transition(db, app, body.new_state, actor=user.username, reason=body.reason)
    except InvalidAppTransition as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return _get(db, app_id)


@router.get("/{app_id}/timeline", response_model=list[ApplicationEventOut])
def timeline(app_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get(db, app_id)
    return (
        db.query(ApplicationEvent)
        .filter(ApplicationEvent.application_id == app_id)
        .order_by(ApplicationEvent.created_at.asc())
        .all()
    )
