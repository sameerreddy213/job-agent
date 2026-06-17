"""Sheet -> DB writeback (two-way sync for the Status columns).

The mirror in sync.py is DB -> Sheet. This module reads back the manual edits a
user makes to the **Status** dropdowns (Jobs + Applications tabs) and applies
them to the database so the dashboard reflects them. Run this BEFORE sync_all so
the Applications tab (which sync overwrites) is read before being clobbered.

Matching has no ID column, so Jobs rows are matched by Apply URL first, then by
the (company, title, location) fingerprint. Manual edits are treated as an
explicit override: we set the status directly (bypassing the transition guard)
but still record a history + audit event with actor "google-sheet".
"""
from sqlalchemy.orm import Session

from .. import applications as apps_mod
from .. import workflow
from ..models.application import Application
from ..models.job import Job
from ..pipeline.fingerprint import fingerprint
from .client import get_spreadsheet, is_configured
from .sync import (
    APP_STATUS_OPTIONS,
    APPLICATIONS_HEADER,
    JOBS_HEADER,
    _retry,
)

ACTOR = "google-sheet"

# The Jobs tab is append-only, so old rows keep the status they had when written
# while the pipeline keeps advancing the DB (DISCOVERED->FILTERED->SCORED->
# REVIEW_QUEUE). To avoid reverting that automatic progress, we only write back
# *manual-action* statuses — the ones a person sets deliberately. Auto/transient
# pipeline states are ignored on writeback. (Applications tab is overwritten each
# sync, so it has no stale rows and all its statuses are honored.)
JOB_MANUAL_STATUSES = {
    workflow.State.APPROVED,
    workflow.State.REJECTED,
    workflow.State.ARCHIVED,
    workflow.State.READY_TO_APPLY,
    workflow.State.APPLIED,
}


def _col(header: list[str], name: str) -> int:
    return header.index(name)


def _pull_jobs(db: Session, ss) -> int:
    import gspread

    try:
        ws = ss.worksheet("Jobs")
    except gspread.WorksheetNotFound:
        return 0
    values = _retry(ws.get_all_values)
    if len(values) < 2:
        return 0

    c_status = _col(JOBS_HEADER, "Status")
    c_url = _col(JOBS_HEADER, "Apply URL")
    c_company = _col(JOBS_HEADER, "Company")
    c_role = _col(JOBS_HEADER, "Role")
    c_loc = _col(JOBS_HEADER, "Location")

    jobs = db.query(Job).all()
    by_url = {j.apply_url: j for j in jobs if j.apply_url}
    by_fp = {j.fingerprint: j for j in jobs}

    changed = 0
    for row in values[1:]:
        if len(row) <= c_status:
            continue
        new_status = (row[c_status] or "").strip()
        if new_status not in JOB_MANUAL_STATUSES:
            continue
        url = row[c_url].strip() if len(row) > c_url else ""
        job = by_url.get(url) if url else None
        if job is None:
            fp = fingerprint(
                row[c_company] if len(row) > c_company else "",
                row[c_role] if len(row) > c_role else "",
                row[c_loc] if len(row) > c_loc else "",
            )
            job = by_fp.get(fp)
        if job is None or job.status == new_status:
            continue
        workflow._record(db, job, job.status, new_status, ACTOR, "edited in Google Sheet")
        job.status = new_status
        job.archived = new_status == workflow.State.ARCHIVED
        changed += 1
    return changed


def _pull_apps(db: Session, ss) -> int:
    import gspread

    try:
        ws = ss.worksheet("Applications")
    except gspread.WorksheetNotFound:
        return 0
    values = _retry(ws.get_all_values)
    if len(values) < 2:
        return 0

    c_status = _col(APPLICATIONS_HEADER, "Status")
    c_company = _col(APPLICATIONS_HEADER, "Company")
    c_role = _col(APPLICATIONS_HEADER, "Role")

    # Map (company, title) -> Application via its job.
    apps = db.query(Application).all()
    index: dict[tuple[str, str], Application] = {}
    for app in apps:
        job = db.get(Job, app.job_id)
        if job:
            index[((job.company or "").strip(), (job.title or "").strip())] = app

    changed = 0
    for row in values[1:]:
        if len(row) <= c_status:
            continue
        new_status = (row[c_status] or "").strip()
        if new_status not in APP_STATUS_OPTIONS:
            continue
        key = (
            row[c_company].strip() if len(row) > c_company else "",
            row[c_role].strip() if len(row) > c_role else "",
        )
        app = index.get(key)
        if app is None or app.status == new_status:
            continue
        apps_mod._record(db, app, app.status, new_status, ACTOR, "edited in Google Sheet")
        app.status = new_status
        if new_status == apps_mod.AppState.SUBMITTED and app.submitted_at is None:
            from datetime import datetime, timezone

            app.submitted_at = datetime.now(timezone.utc)
        changed += 1
    return changed


def pull_changes(db: Session) -> dict:
    """Apply Status edits from the sheet back into the DB. Best-effort."""
    if not is_configured():
        return {"status": "not_configured"}
    try:
        ss = _retry(get_spreadsheet)
        jobs_changed = _pull_jobs(db, ss)
        apps_changed = _pull_apps(db, ss)
        db.commit()
        return {"status": "success", "jobs": jobs_changed, "applications": apps_changed}
    except Exception as e:  # noqa: BLE001
        db.rollback()
        return {"status": "failed", "error": str(e)}
