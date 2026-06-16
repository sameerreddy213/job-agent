import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..applications import (
    ALL_APP_STATES,
    AppState,
    InvalidAppTransition,
    get_or_create,
    transition,
)
from ..applications import provision_for_job
from ..audit import write_audit
from ..deps import get_current_user, get_db
from ..models.application import Application, ApplicationEvent
from ..models.job import Job
from ..models.user import User
from ..schemas.application import (
    ApplicationAnalytics,
    ApplicationDetailOut,
    ApplicationEventOut,
    ApplicationOut,
    CreateApplicationBody,
    StateCount,
    TransitionBody,
    UpdateApplicationBody,
)

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
