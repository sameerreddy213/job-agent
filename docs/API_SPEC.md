# API Spec — job-agent

Base path behind Nginx: `https://jobs.<domain>/api/` (Nginx strips `/api/`, so the
FastAPI app serves routes at root). All routes require a Bearer JWT except
`/health` and `/auth/login`.

## Phase 1 routes (current)

### Health
- `GET /health` → `{ "status": "ok", "phase": 1 }`
- `GET /health/db` → checks DB connectivity → `{ "status": "ok", "db": "up" }`

### Auth
- `POST /auth/login` (form: `username`, `password`) → `{ access_token, refresh_token, token_type }`
- `POST /auth/refresh` `{ refresh_token }` → new token pair
- `GET /auth/me` → current user

### Profile (singleton)
- `GET /profile` → profile
- `PUT /profile` → upsert profile fields

### Resumes (versioned)
- `GET /resumes` → categories with current version summary
- `GET /resumes/{category}/versions` → all versions
- `POST /resumes/{category}/versions` (multipart file upload) → creates new version, sets current
- `POST /resumes/{category}/rollback/{version_number}` → sets that version current

## Phase 2 routes (current)

### Sources
- `GET /sources` → configured sources (name, kind, apply_policy, enabled, config, last run)
- `PATCH /sources/{id}` `{enabled?, apply_policy?, config?}` → update a source

### Jobs
- `GET /jobs?status=&source=&min_score=&archived=&limit=&offset=` → filtered list (with score)
- `GET /jobs/{id}` → job detail (includes description)

### Pipeline / health
- `POST /admin/run-now` → trigger one discovery run synchronously (returns per-source summary)
- `GET /health/sources` → latest run health per source (HEALTHY / WARNING / FAILED)

### Metrics (Phase 4 observability, public like /health)
- `GET /metrics` → Prometheus exposition text. Counters: `jobs_found`, `jobs_filtered`,
  `jobs_scored`, `pipeline_runs`, `pipeline_failures`, `login_success`, `login_failure`
  (computed from the DB so they're consistent across the api + worker processes)
- `GET /metrics.json` → same counters as JSON

## Phase 3 routes (dashboard backend — current)

### Auth (extended)
- `POST /auth/logout` `{refresh_token}` → revoke refresh token (204)
- Login is rate-limited (`LOGIN_MAX_ATTEMPTS` per `LOGIN_WINDOW_SECONDS` → 429).
- Refresh tokens rotate on `/auth/refresh` (old token revoked).

### Queue
- `GET /queue?classification=&source=&min_score=&limit=&offset=` → actionable jobs (auto+review), score desc
- `GET /queue/counts` → `{auto_eligible, review_queue}`

### Dashboard
- `GET /dashboard/summary` → cards: totals, new today, auto/review/rejected/archived, per-source health

### Analytics
- `GET /analytics/overview?days=&top_n=` → jobs/day, top companies, top locations, top skills,
  resume stats; applications/interview metrics are placeholders until Phase 5

### Resumes (dashboard)
- `GET /resumes/summary` → per category: current version, previous-version count, last updated

### Settings
- `GET /settings` → scan interval, test mode, retention, scoring weights, thresholds
- `GET/POST /settings/blacklist/companies`, `DELETE /settings/blacklist/companies/{id}`
- `GET/POST /settings/blacklist/keywords`, `DELETE /settings/blacklist/keywords/{id}`

### Audit
- `GET /audit?action=&actor=&limit=&offset=` → audit log entries (newest first)

## Phase 5A routes (resume intelligence — current)
- `POST /jobs/{id}/rematch` → re-run the rule-based resume recommendation using
  current resumes; updates the job's score with selected resume, match score,
  matched/missing skills, confidence, and reasoning.
- `POST /jobs/{id}/resume` `{category}` → manually override the selected resume
  (recomputes matched/missing skills vs that resume; `resume_override=true`).

`ScoreOut` now also includes: `resume_match_score`, `resume_confidence`,
`matched_skills[]`, `missing_skills[]`, `resume_reasoning`, `resume_override`.
Resume uploads now parse the file (PDF/DOCX/TXT) and store `skills_detected` +
`detected_category` (rule engine, no LLM).

## Phase 6A routes (materials generation — current)
- `POST /jobs/{id}/materials/generate?cover_letter=true&category=<cat>` → generate
  (or regenerate) a truthful application packet from profile + selected resume;
  returns cover-letter / résumé-summary text, application answers, and available formats.
- `GET /jobs/{id}/materials` → fetch the current packet.
- `GET /jobs/{id}/materials/download/{txt|docx|pdf}` → download the export file.

`/metrics` adds `refresh_reuse_detected`. Auth `/auth/refresh` now performs
refresh-token **reuse detection** (revokes the whole token family on reuse).

## Phase 6B routes (Google Sheets mirror — current)
- `POST /admin/sync-sheets` → run a one-way DB→Sheets mirror; returns
  `{status: success|not_configured|failed, rows_written, duration_ms, tabs}`.
- `GET /admin/sync-sheets/status` → configured/enabled flags, last sync time,
  status, rows written, latency, last error.

Tabs mirrored: **Jobs, Applications, Sources, Runs, Resume Stats** (DB stays the
source of truth; one-way). `/metrics` adds `sync_success`, `sync_failure`,
`rows_written`, `sheet_latency_ms`.

## Phase 6C routes (Telegram — current)
- `GET /settings/telegram` → enabled, chat_id, notification preferences, `configured`
  (whether a bot token is present; token itself is never returned).
- `PUT /settings/telegram` → update enabled / chat_id / per-event preferences.

Notifications (worker, notify-only — no approvals): high-match (90+), daily 09:00 IST,
evening 18:00 IST, pipeline failure, Sheets failure, security (refresh reuse).
Bot commands (read-only): `/stats`, `/health`, `/sync-status`, `/latest-jobs`.
`/metrics` adds `telegram_sent`, `telegram_failed`, `telegram_retried`.

## Phase 7A routes (workflow engine — current)
Job workflow states: DISCOVERED, FILTERED, SCORED, REVIEW_QUEUE, APPROVED, REJECTED,
MATERIALS_GENERATED, READY_TO_APPLY, APPLIED, FAILED, ARCHIVED. Transitions are
validated by a state machine; every transition is recorded to `job_state_history`
and the audit log.

- `POST /jobs/{id}/approve` · `POST /jobs/{id}/reject` · `POST /jobs/{id}/archive`
  · `POST /jobs/{id}/snooze` (`{hours}`)
- `POST /jobs/bulk/approve|reject|archive` (`{ids: [...]}`) → per-id results
- `GET /jobs/{id}/workflow/history` → ordered transitions
- `GET /workflow/state-counts` → count per state
- `GET /workflow/pending-review` → jobs in REVIEW_QUEUE
- Illegal transitions return **409**. `/metrics` adds `workflow_transitions`,
  `workflow_failures`, `jobs_approved`, `jobs_rejected`, `jobs_archived`.

## Phase 7B routes (workflow completion — current)
Analytics and timelines over the workflow history. No browser automation / no submission.

- `GET /workflow/timeline?job_id=&limit=&offset=` → transition feed joined with
  job company/title. With `job_id`: full per-job timeline (oldest first); without:
  global recent feed (newest first).
- `GET /workflow/analytics?days=` → `jobs_by_state`, `total_transitions`,
  `approvals`, `rejections`, `snoozes`, `archives`, `decisions`,
  `approval_pct`/`rejection_pct`/`snooze_pct`, `avg_review_seconds`,
  `pending_review_trend` (per-day jobs entering REVIEW_QUEUE).
- `GET /workflow/approval-stats?days=` → `approved`/`rejected`/`archived`/`snoozed`
  counts, `approval_rate`/`rejection_rate`, `approved_per_day`, `rejected_per_day`.
- `GET /audit?entity=&entity_id=` → audit log filtered to one entity (e.g. a job).
- Avg review time = mean seconds from a job entering REVIEW_QUEUE to its first
  decision (APPROVED/REJECTED/ARCHIVED). Snoozes are history rows where
  `previous_state == new_state`.
- Dashboard: workflow metrics card (approval/rejection/snooze rates, avg review
  time, jobs-by-state, pending-review trend). Queue: workflow status badges,
  transition-history modal, bulk-action confirmation, review statistics.
  Job detail: workflow timeline + audit history + material status.

## Phase 8A routes (application engine — current)
Tracks applications only — **no submission, no browser automation, no Playwright.**
SUBMITTED merely records that the user submitted elsewhere. Application states:
NOT_STARTED, READY, IN_PROGRESS, SUBMITTED, INTERVIEW, ASSESSMENT, REJECTED,
OFFER, ACCEPTED, WITHDRAWN (state machine enforced; illegal transitions → **409**).

On job approval (`POST /jobs/{id}/approve`): materials are generated, an
`applications` row is created, documents/answers are linked, and the application
moves to READY (best-effort — if materials can't be generated yet it stays
NOT_STARTED with an explanatory event).

- `GET /applications?status=&job_id=` · `POST /applications` (`{job_id}`)
  · `GET /applications/{id}` · `PATCH /applications/{id}` (`{notes, resume_category}`)
  · `DELETE /applications/{id}`
- `POST /applications/{id}/transition` (`{new_state, reason}`)
- `GET /applications/{id}/timeline` → ordered state events
- `GET /applications/analytics` → totals, by-state counts, funnel rates
  (submit/interview/offer/acceptance)
- Tables: `applications`, `application_documents`, `application_answers`,
  `application_events`. `/metrics` adds `applications_created`,
  `applications_submitted`, `interviews`, `offers`, `rejections`.

## Phase 8B routes (ATS integration layer — current)
Understands *where* an application would be submitted and whether it's complete.
**No submission, no browser automation, no Playwright** — ATS detection is pure
analysis of the apply URL host. Detected types: GREENHOUSE, LEVER, ASHBY, WORKDAY,
SMARTRECRUITERS, JOBVITE, BAMBOOHR, CUSTOM (real URL, unknown host), UNKNOWN (no URL).

Per application we store `ats_type`, `ats_version` (e.g. Workday `wd3`),
`application_url`, `supports_easy_apply`, `requires_manual_fields` (set on
provisioning; refreshable). Readiness engine scores material completeness
(materials 40 + resume 30 + answers 30 = 100); `ready` requires a full packet
AND no manual fields.

- `GET /applications/readiness?ready_only=` → applications + readiness summary
- `GET /applications/ready-queue` → fully-ready applications
- `GET /applications/ats-breakdown` → totals, detected/unknown, ready/manual, by-ATS
- `GET /applications/{id}/readiness` → ready_score, ready, missing_*,
  manual_review_required, reasons
- `POST /applications/{id}/detect-ats` → re-run detection
- `/metrics` adds `ready_to_apply`, `manual_review_required`, `ats_detected`,
  `ats_unknown`. Migration `0010` adds the ATS columns.

## Phase 8C routes (manual apply assistant — current)
Helps the user apply **manually**. No submission, no browser automation, no Playwright.

- `GET /applications/{id}/checklist` → checklist items ({key,label,done,required}),
  `complete` (all required done), `ready_confirmed`.
- `POST /applications/{id}/confirm-ready` → records the user's intent to apply
  (sets `ready_confirmed`); never submits.
- `POST /applications/{id}/packet` → builds a self-contained packet (Resume +
  Cover Letter + Application Answers + Application Notes) as TXT/DOCX/PDF.
  400 if materials not yet generated.
- `GET /applications/{id}/packet` → packet status + available formats.
- `GET /applications/{id}/packet/download/{fmt}` → download (txt/docx/pdf);
  records a download audit event.
- `/metrics` adds `application_packets_generated`, `application_packets_downloaded`,
  `ready_to_apply_confirmed`. Migration `0011` adds packet/confirmation columns.

## Planned (later phases — not implemented yet)
Apply engine / auto-submit (READY_TO_APPLY → APPLIED). Submission remains manual.

## Auth header
```
Authorization: Bearer <access_token>
```
Interactive docs at `/docs` (Swagger) when running.
