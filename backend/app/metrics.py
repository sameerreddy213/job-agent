"""Metrics computed from the database so they are consistent across the api and
worker processes (the pipeline runs in the worker; /metrics is served by the api).

Exposed counters:
  jobs_found, jobs_filtered, jobs_scored, pipeline_runs, pipeline_failures,
  login_success, login_failure
"""
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from .applications import AppState
from .ats import AtsDetection, AtsType, evaluate_readiness
from .models.application import Application, ApplicationEvent
from .models.audit import AuditLog
from .models.job import Job, JobScore, RunHealth
from .models.sync import SheetSyncRun
from .models.telegram import TelegramEvent
from .models.workflow import JobStateHistory
from .workflow import State

_HELP = {
    "jobs_found": "Total jobs discovered across all pipeline runs",
    "jobs_filtered": "Jobs rejected by the fresher/blacklist filter",
    "jobs_scored": "Jobs that passed filtering and were scored",
    "pipeline_runs": "Per-source pipeline executions recorded",
    "pipeline_failures": "Per-source pipeline executions that failed",
    "login_success": "Successful logins",
    "login_failure": "Failed logins",
    "refresh_reuse_detected": "Refresh-token reuse events (forced session revocation)",
    "sync_success": "Successful Google Sheets syncs",
    "sync_failure": "Failed Google Sheets syncs",
    "rows_written": "Total rows written to Google Sheets",
    "sheet_latency_ms": "Duration of the most recent Sheets sync (ms)",
    "telegram_sent": "Telegram messages sent successfully",
    "telegram_failed": "Telegram messages that failed to send",
    "telegram_retried": "Total Telegram send retries",
    "workflow_transitions": "Total job workflow-state transitions",
    "workflow_failures": "Transitions into the FAILED state",
    "jobs_approved": "Jobs approved",
    "jobs_rejected": "Jobs rejected",
    "jobs_archived": "Jobs archived",
    "applications_created": "Applications created",
    "applications_submitted": "Applications that reached SUBMITTED",
    "interviews": "Applications that reached INTERVIEW",
    "offers": "Applications that reached OFFER",
    "rejections": "Applications that reached REJECTED",
    "ready_to_apply": "Applications fully ready with no manual fields required",
    "manual_review_required": "Applications needing manual fields/review",
    "ats_detected": "Applications with a recognised ATS",
    "ats_unknown": "Applications with no detectable ATS",
    "application_packets_generated": "Manual-apply packets generated",
    "application_packets_downloaded": "Manual-apply packet downloads",
    "ready_to_apply_confirmed": "Applications the user confirmed ready to apply",
}


def compute_metrics(db: Session) -> dict[str, int]:
    jobs_found = db.query(func.coalesce(func.sum(RunHealth.jobs_found), 0)).scalar() or 0
    pipeline_runs = db.query(func.count(RunHealth.id)).scalar() or 0
    pipeline_failures = (
        db.query(func.count(RunHealth.id)).filter(RunHealth.status == "FAILED").scalar() or 0
    )
    jobs_filtered = (
        db.query(func.count(Job.id)).filter(Job.status == State.FILTERED).scalar() or 0
    )

    def _hist(state: str) -> int:
        return db.query(func.count(JobStateHistory.id)).filter(JobStateHistory.new_state == state).scalar() or 0

    workflow_transitions = db.query(func.count(JobStateHistory.id)).scalar() or 0
    workflow_failures = _hist(State.FAILED)
    jobs_approved = _hist(State.APPROVED)
    jobs_rejected = _hist(State.REJECTED)
    jobs_archived = _hist(State.ARCHIVED)
    jobs_scored = (
        db.query(func.count(JobScore.id)).filter(JobScore.passed_filters.is_(True)).scalar() or 0
    )
    login_success = (
        db.query(func.count(AuditLog.id)).filter(AuditLog.action == "login.success").scalar() or 0
    )
    login_failure = (
        db.query(func.count(AuditLog.id)).filter(AuditLog.action == "login.failed").scalar() or 0
    )
    refresh_reuse = (
        db.query(func.count(AuditLog.id)).filter(AuditLog.action == "security.refresh_reuse").scalar() or 0
    )
    sync_success = (
        db.query(func.count(SheetSyncRun.id)).filter(SheetSyncRun.status == "success").scalar() or 0
    )
    sync_failure = (
        db.query(func.count(SheetSyncRun.id)).filter(SheetSyncRun.status == "failed").scalar() or 0
    )
    rows_written = (
        db.query(func.coalesce(func.sum(SheetSyncRun.rows_written), 0)).scalar() or 0
    )
    last_run = db.query(SheetSyncRun).order_by(SheetSyncRun.run_at.desc()).first()
    sheet_latency = last_run.duration_ms if last_run else 0
    tg_sent = db.query(func.count(TelegramEvent.id)).filter(TelegramEvent.status == "sent").scalar() or 0
    tg_failed = db.query(func.count(TelegramEvent.id)).filter(TelegramEvent.status == "failed").scalar() or 0
    tg_retried = db.query(func.coalesce(func.sum(TelegramEvent.retries), 0)).scalar() or 0

    def _app_ev(state: str) -> int:
        return (
            db.query(func.count(func.distinct(ApplicationEvent.application_id)))
            .filter(ApplicationEvent.new_state == state)
            .scalar()
            or 0
        )

    applications_created = db.query(func.count(Application.id)).scalar() or 0
    applications_submitted = _app_ev(AppState.SUBMITTED)
    interviews = _app_ev(AppState.INTERVIEW)
    offers = _app_ev(AppState.OFFER)
    rejections = _app_ev(AppState.REJECTED)

    # ATS / readiness counters (Phase 8B).
    ready_to_apply = manual_review_required = ats_detected = ats_unknown = 0
    apps = (
        db.query(Application)
        .options(selectinload(Application.documents), selectinload(Application.answers))
        .all()
    )
    for app in apps:
        if app.ats_type == AtsType.UNKNOWN:
            ats_unknown += 1
        else:
            ats_detected += 1
        report = evaluate_readiness(
            has_documents=len(app.documents) > 0,
            resume_category=app.resume_category,
            answer_count=len(app.answers),
            ats=AtsDetection(
                ats_type=app.ats_type, ats_version=app.ats_version,
                application_url=app.application_url,
                supports_easy_apply=app.supports_easy_apply,
                requires_manual_fields=app.requires_manual_fields,
            ),
        )
        if report.ready:
            ready_to_apply += 1
        if report.manual_review_required:
            manual_review_required += 1

    packets_generated = (
        db.query(func.count(AuditLog.id)).filter(AuditLog.action == "application.packet_generated").scalar() or 0
    )
    packets_downloaded = (
        db.query(func.count(AuditLog.id)).filter(AuditLog.action == "application.packet_downloaded").scalar() or 0
    )
    ready_confirmed = (
        db.query(func.count(Application.id)).filter(Application.ready_confirmed.is_(True)).scalar() or 0
    )
    return {
        "jobs_found": int(jobs_found),
        "jobs_filtered": int(jobs_filtered),
        "jobs_scored": int(jobs_scored),
        "pipeline_runs": int(pipeline_runs),
        "pipeline_failures": int(pipeline_failures),
        "login_success": int(login_success),
        "login_failure": int(login_failure),
        "refresh_reuse_detected": int(refresh_reuse),
        "sync_success": int(sync_success),
        "sync_failure": int(sync_failure),
        "rows_written": int(rows_written),
        "sheet_latency_ms": int(sheet_latency),
        "telegram_sent": int(tg_sent),
        "telegram_failed": int(tg_failed),
        "telegram_retried": int(tg_retried),
        "workflow_transitions": int(workflow_transitions),
        "workflow_failures": int(workflow_failures),
        "jobs_approved": int(jobs_approved),
        "jobs_rejected": int(jobs_rejected),
        "jobs_archived": int(jobs_archived),
        "applications_created": int(applications_created),
        "applications_submitted": int(applications_submitted),
        "interviews": int(interviews),
        "offers": int(offers),
        "rejections": int(rejections),
        "ready_to_apply": int(ready_to_apply),
        "manual_review_required": int(manual_review_required),
        "ats_detected": int(ats_detected),
        "ats_unknown": int(ats_unknown),
        "application_packets_generated": int(packets_generated),
        "application_packets_downloaded": int(packets_downloaded),
        "ready_to_apply_confirmed": int(ready_confirmed),
    }


def render_prometheus(values: dict[str, int]) -> str:
    lines: list[str] = []
    for name, value in values.items():
        lines.append(f"# HELP {name} {_HELP.get(name, name)}")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"
