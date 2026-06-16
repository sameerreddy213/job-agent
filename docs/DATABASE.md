# Database — job-agent

PostgreSQL 16. Migrations via Alembic. Extensions: `pgcrypto`, `citext`, `pg_trgm`.

## Phase 1 tables (current)

### users
Single admin. `id (uuid)`, `username (citext, unique)`, `password_hash (argon2)`,
`role`, `created_at`.

### profile
Singleton (`CHECK id = 1`). Identity used for form-fill: `full_name`, `email (citext)`,
`phone`, `location`, `notice_period`, `experience_level`, `work_auth`,
`relocation (bool)`, `expected_ctc`, `linkedin_url`, `github_url`, `portfolio_url`,
`updated_at`.

### resumes
One row per role category. `id (uuid)`, `category (unique)`, `is_active`, `created_at`.

### resume_versions  (versioning)
`id (uuid)`, `resume_id (fk→resumes, cascade)`, `version_number (int)`, `file_path`,
`skills_detected (jsonb)`, `role_category`, `upload_date`, `is_current (bool)`.
Unique `(resume_id, version_number)`.

**Versioning rules:** uploading a new file for a category appends a new
`version_number` and flips `is_current`. Old versions are kept. Rollback sets an
older version `is_current = true`. Skill detection is a later phase (empty list now).

## Phase 2 tables (current)

### sources
`id`, `name (unique)`, `kind (ats|company|board)`, `apply_policy (auto|manual)`,
`enabled`, `config (jsonb)` (e.g. `{"boards":[...]}` / `{"companies":[...]}`),
`last_run`, `last_status`, `last_error`, `created_at`.

### jobs
Normalized schema + dedupe. `id (uuid)`, `source`, `external_id`,
`fingerprint (unique)`, `company`, `title`, `location`, `description`,
`experience`, `apply_url`, `posted_date`, `employment_type`, `remote_status`,
`raw (jsonb)`, `status`, `discovered_at`, `archived`.
Indexes on `status`, `source`, `discovered_at`.

### job_scores
`job_id (fk, unique)`, `freshers_score`, `skills_score`, `location_score`,
`role_score`, `total_score`, `classification`, `matched_resume_category`,
`reasoning`, `passed_filters`, `scored_at`. Index on `total_score`.

### run_health
`source`, `run_at`, `jobs_found`, `new_jobs`, `errors`, `response_time_ms`,
`status (HEALTHY|WARNING|FAILED)`, `detail`.

## Phase 3 tables (current)

### refresh_tokens
`jti (unique)`, `user_id (fk)`, `expires_at`, `revoked`, `created_at` — enables
refresh-token rotation + logout/revocation.

### company_blacklist
`company (citext, unique)`, `reason`, `created_at`.

### keyword_blacklist
`keyword (citext, unique)`, `applies_to (title|description|both)`, `reason`, `created_at`.

### audit_log
`actor`, `action`, `entity`, `entity_id`, `payload (jsonb)`, `created_at`. Indexed on
`created_at`, `action`.

### sources (extended)
Added `display_name`, `website`, `rate_limit_per_min`, `meta (jsonb)`.

## Phase 5A additions (resume intelligence)
- **job_scores** + `resume_match_score`, `resume_confidence`, `matched_skills (jsonb)`,
  `missing_skills (jsonb)`, `resume_reasoning`, `resume_override`.
- **resume_versions** + `detected_category`, `categorization_confidence`
  (populated by rule-based parsing on upload).

## Phase 6A additions
- **refresh_tokens** + `family_id` (token-family reuse detection).
- **materials** (one packet per job): `job_id (fk, unique)`, `resume_category`,
  `cover_letter_required`, `cover_letter_text`, `resume_summary_text`,
  `application_answers (jsonb)`, `txt_path`, `docx_path`, `pdf_path`, `generated_at`.

## Phase 6B additions (Google Sheets mirror)
- **run_health** + `filtered`, `scored` (per-run counters for the Runs tab).
- **sync_state** (singleton): `jobs_cursor`, `runs_cursor` (incremental-sync cursors).
- **sheet_sync_runs**: `run_at`, `status (success|failed|skipped)`, `rows_written`,
  `duration_ms`, `error`, `tabs (jsonb)` — drives sync status + metrics.

## Phase 6C additions (Telegram)
- **jobs** + `high_match_notified` (de-dupes high-match alerts).
- **telegram_settings** (singleton): `enabled`, `chat_id`, `pref_*` per-event flags,
  `last_update_id` (getUpdates offset). Bot token is env-only, never stored.
- **telegram_events**: `kind`, `status (sent|failed)`, `retries`, `error` — drives
  `telegram_*` metrics.

## Phase 7A additions (workflow engine)
- **jobs** + `snoozed_until`. `jobs.status` now holds the **workflow state**
  (migration backfills legacy AUTO_APPROVE_ELIGIBLE→REVIEW_QUEUE, REJECT→REJECTED,
  REJECTED_FILTER→FILTERED). Score classification lives in `job_scores.classification`.
- **job_state_history**: `job_id (fk)`, `previous_state`, `new_state`, `actor`,
  `reason`, `created_at` — append-only transition audit (also mirrored to audit_log).

## Planned tables (later phases — NOT created yet)
`applications`, analytics aggregates.

## Conventions
- UUID PKs via `gen_random_uuid()` (pgcrypto).
- Timestamps `timestamptz` default `now()`.
- Dedupe (Phase 2): `fingerprint = sha256(norm(title)|norm(company)|norm(location))`.
- Retention (Phase 6): archive after 365 days.

## Migrations
```bash
alembic revision -m "msg"     # create
alembic upgrade head          # apply (run automatically by api entrypoint)
alembic downgrade -1          # rollback one
```
