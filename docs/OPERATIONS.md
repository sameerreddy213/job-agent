# Operations — job-agent

## Day-to-day
```bash
docker compose ps                 # service status
docker compose logs -f api        # tail API logs
docker compose logs -f worker     # tail pipeline logs
./scripts/deploy.sh               # pull + build + restart
```

## Health checks
- `GET /api/health` → liveness · `GET /api/health/db` → DB connectivity
- Container healthchecks (all four services): **api** (HTTP /health), **postgres**
  (`pg_isready`), **worker** (heartbeat file refreshed every 60s; stale >180s = unhealthy),
  **nginx** (`/healthz` on port 80).
- `docker compose ps` shows health status per container.

## Observability
- **Structured JSON logs** on stdout (one object per line) with fields:
  `timestamp, level, service, request_id, user, action, status, duration_ms, message`.
  View: `docker compose logs -f api` / `worker`. Each HTTP response carries `X-Request-ID`.
- **Metrics:** `GET /api/metrics` (Prometheus) or `/api/metrics.json` — `jobs_found`,
  `jobs_filtered`, `jobs_scored`, `pipeline_runs`, `pipeline_failures`,
  `login_success`, `login_failure`, `refresh_reuse_detected`,
  `sync_success`, `sync_failure`, `rows_written`, `sheet_latency_ms`,
  `telegram_sent`, `telegram_failed`, `telegram_retried`,
  `workflow_transitions`, `workflow_failures`, `jobs_approved`, `jobs_rejected`, `jobs_archived`.

## Telegram notifications (Phase 6C)
- Notify-only (no approval actions). Set `TELEGRAM_BOT_TOKEN` (env-only secret),
  set chat id + per-event preferences + enable in **Settings → Telegram**.
- Events: high-match (90+), daily 09:00 IST, evening 18:00 IST, pipeline failure,
  Sheets failure, security (refresh-token reuse). Scheduled in the worker.
- Read-only commands (worker polls getUpdates): `/stats`, `/health`,
  `/sync-status`, `/latest-jobs`.
- Sends use a per-chat rate limit + retry (honors 429 `retry_after`); each attempt
  logged to `telegram_events`.

## Google Sheets mirror (Phase 6B)
- One-way DB→Sheets mirror; DB remains source of truth. Configure
  `GOOGLE_SHEET_ID` + `GOOGLE_SERVICE_ACCOUNT_JSON` (or `_FILE`), share the sheet
  with the service-account email, set `SHEETS_SYNC_ENABLED=true`.
- Manual: `POST /api/admin/sync-sheets`. Scheduled: every
  `SHEETS_SYNC_INTERVAL_MINUTES` in the worker (only when enabled + configured).
- Jobs/Runs append incrementally (cursor-tracked); Sources/Resume Stats/Applications
  overwrite. Retries with backoff; each attempt logged to `sheet_sync_runs`.

## Migrations
Run automatically by the `api` container on start (`RUN_MIGRATIONS=true` →
`alembic upgrade head` then admin seed). Manual:
```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
```

## Admin seeding
On first boot the `api` container creates the admin from `ADMIN_USERNAME` /
`ADMIN_PASSWORD`. To rotate: change `.env`, then
`docker compose exec api python -m app.seed` (idempotent; won't duplicate).

## Backups (cron)
```
0 2 * * *  scripts/backup-db.sh       # DB dump (local, git-ignored)
0 3 * * *  scripts/github-backup.sh   # config/infra → GitHub
```

## TLS renewal
`certbot` container renews every 12h automatically. Force:
```bash
docker compose run --rm certbot renew --force-renewal
docker compose restart nginx
```

## Monitoring (Phase 6 / future)
- Telegram alerts: daily summary, high-match jobs, errors, scraper health
  (0-results / failure / login-expiry).
- CloudWatch: host + container metrics, log shipping, billing alarms.

## Incident quick refs
- API 500s → `docker compose logs api`; check DB up via `/api/health/db`.
- Cert expired → re-run certbot renew + restart nginx.
- Disk full → prune images `docker image prune -f`, check `./backups` size.
