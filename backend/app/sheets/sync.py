"""One-way DB -> Google Sheets mirror with retry + incremental sync.

Jobs and Runs are appended incrementally (cursor-tracked). Sources, Resume Stats,
and Applications are small/derived and fully overwritten each sync.
"""
import time
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.application import Application
from ..models.job import Job, JobScore, RunHealth
from ..models.material import Material
from ..models.resume import Resume
from ..models.source import Source
from ..models.sync import SheetSyncRun, SyncState
from .client import get_spreadsheet, is_configured

# Tab headers (exact column orders requested).
JOBS_HEADER = ["Date", "Company", "Role", "Location", "Source", "Score", "Resume Selected", "Confidence", "Status", "Apply URL"]
APPLICATIONS_HEADER = ["Date", "Company", "Role", "Resume Used", "Cover Letter", "Status", "Notes"]
SOURCES_HEADER = ["Source", "Enabled", "Health", "Last Run", "Jobs Found"]
RUNS_HEADER = ["Run Date", "Duration (ms)", "Jobs Found", "Filtered", "Scored", "Errors"]
RESUME_STATS_HEADER = ["Resume Category", "Jobs Matched", "Success Rate", "Last Used"]


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _retry(fn, *args, attempts: int = 3, **kwargs):
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** i)
    raise last  # type: ignore[misc]


def _ensure_ws(ss, title: str, header: list[str]):
    import gspread

    try:
        return ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = _retry(ss.add_worksheet, title=title, rows=1000, cols=max(10, len(header)))
        _retry(ws.update, [header], value_input_option="RAW")
        return ws


def _overwrite(ws, header: list[str], rows: list[list]):
    _retry(ws.clear)
    _retry(ws.update, [header] + rows, value_input_option="USER_ENTERED")


def _append(ws, rows: list[list]):
    if rows:
        _retry(ws.append_rows, rows, value_input_option="USER_ENTERED")


# --------------------------------------------------------------------------- #
# Row builders
# --------------------------------------------------------------------------- #
def _jobs_rows(db: Session, cursor: datetime | None):
    q = db.query(Job)
    if cursor:
        q = q.filter(Job.discovered_at > cursor)
    jobs = q.order_by(Job.discovered_at.asc()).all()
    rows = []
    newest = cursor
    for j in jobs:
        s = j.score
        rows.append([
            _fmt(j.discovered_at), j.company, j.title, j.location or "", j.source,
            s.total_score if s else "", s.matched_resume_category if s else "",
            s.resume_confidence if s else "", j.status, j.apply_url or "",
        ])
        if newest is None or (j.discovered_at and j.discovered_at > newest):
            newest = j.discovered_at
    return rows, newest


def _runs_rows(db: Session, cursor: datetime | None):
    q = db.query(RunHealth)
    if cursor:
        q = q.filter(RunHealth.run_at > cursor)
    runs = q.order_by(RunHealth.run_at.asc()).all()
    rows = []
    newest = cursor
    for r in runs:
        rows.append([_fmt(r.run_at), r.response_time_ms, r.jobs_found, r.filtered, r.scored, r.errors])
        if newest is None or (r.run_at and r.run_at > newest):
            newest = r.run_at
    return rows, newest


def _sources_rows(db: Session):
    latest: dict[str, RunHealth] = {}
    for r in db.query(RunHealth).order_by(RunHealth.run_at.desc()).all():
        latest.setdefault(r.source, r)
    rows = []
    for s in db.query(Source).order_by(Source.name).all():
        run = latest.get(s.name)
        rows.append([
            s.name, "Yes" if s.enabled else "No",
            (run.status if run else s.last_status) or "—",
            _fmt(s.last_run or (run.run_at if run else None)),
            run.jobs_found if run else 0,
        ])
    return rows


def _applications_rows(db: Session):
    """Applied/application details for the Applications tab (overwritten each sync)."""
    rows = []
    apps = db.query(Application).order_by(Application.updated_at.desc()).all()
    for app in apps:
        job = db.get(Job, app.job_id)
        mat = db.query(Material).filter(Material.job_id == app.job_id).first()
        cover = "Yes" if (mat and mat.cover_letter_text) else "No"
        rows.append([
            _fmt(app.submitted_at or app.created_at),
            job.company if job else "",
            job.title if job else "",
            app.resume_category or "",
            cover,
            app.status,
            (app.notes or "").replace("\n", " "),
        ])
    return rows


def _resume_stats_rows(db: Session):
    rows = []
    for resume in db.query(Resume).order_by(Resume.category).all():
        matched = (
            db.query(func.count(JobScore.id))
            .filter(JobScore.matched_resume_category == resume.category)
            .scalar()
            or 0
        )
        # success_rate / last_used require the applications table (later phase).
        rows.append([resume.category, matched, "0%", "—"])
    return rows


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def sync_all(db: Session) -> dict:
    start = time.monotonic()

    if not is_configured():
        db.add(SheetSyncRun(status="skipped", error="Google Sheets not configured"))
        db.commit()
        return {"status": "not_configured"}

    try:
        ss = _retry(get_spreadsheet)
        state = db.get(SyncState, 1)
        if state is None:
            state = SyncState(id=1)
            db.add(state)
            db.flush()

        tabs: dict[str, int] = {}

        # Jobs (incremental append)
        jrows, jcur = _jobs_rows(db, state.jobs_cursor)
        _append(_ensure_ws(ss, "Jobs", JOBS_HEADER), jrows)
        tabs["Jobs"] = len(jrows)
        state.jobs_cursor = jcur

        # Runs (incremental append)
        rrows, rcur = _runs_rows(db, state.runs_cursor)
        _append(_ensure_ws(ss, "Runs", RUNS_HEADER), rrows)
        tabs["Runs"] = len(rrows)
        state.runs_cursor = rcur

        # Sources (overwrite)
        srows = _sources_rows(db)
        _overwrite(_ensure_ws(ss, "Sources", SOURCES_HEADER), SOURCES_HEADER, srows)
        tabs["Sources"] = len(srows)

        # Resume Stats (overwrite)
        rsrows = _resume_stats_rows(db)
        _overwrite(_ensure_ws(ss, "Resume Stats", RESUME_STATS_HEADER), RESUME_STATS_HEADER, rsrows)
        tabs["Resume Stats"] = len(rsrows)

        # Applications (overwrite with real applied details)
        arows = _applications_rows(db)
        _overwrite(_ensure_ws(ss, "Applications", APPLICATIONS_HEADER), APPLICATIONS_HEADER, arows)
        tabs["Applications"] = len(arows)

        rows_written = sum(tabs.values())
        duration_ms = int((time.monotonic() - start) * 1000)
        db.add(SheetSyncRun(status="success", rows_written=rows_written, duration_ms=duration_ms, tabs=tabs))
        db.commit()
        return {"status": "success", "rows_written": rows_written, "duration_ms": duration_ms, "tabs": tabs}

    except Exception as e:  # noqa: BLE001
        db.rollback()
        duration_ms = int((time.monotonic() - start) * 1000)
        db.add(SheetSyncRun(status="failed", duration_ms=duration_ms, error=str(e)[:1000]))
        db.commit()
        return {"status": "failed", "error": str(e), "duration_ms": duration_ms}
