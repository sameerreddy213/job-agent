# Backup Strategy — job-agent

Two independent backup tracks. Sensitive data is NEVER pushed to GitHub.

## 1. Database backups (data) — stays off GitHub
- `scripts/backup-db.sh` runs nightly (cron 02:00): `pg_dump | gzip` → `./backups/`.
- `./backups/` is git-ignored. Local retention: 14 days (configurable).
- **Future (S3):** sync `./backups/` to `s3://<bucket>/job-agent/` via EC2 IAM role
  for off-host durability; apply S3 lifecycle (e.g. expire after 90 days).

## 2. Code / infra / config backups — GitHub
- `scripts/github-backup.sh` runs daily (cron 03:00): commits tracked changes and
  pushes to `github.com/sameerreddy213/job-agent`.
- Aborts if any sensitive file is staged.
- CI workflow `.github/workflows/backup.yml` (01:00 UTC) asserts no secrets/resumes/
  dumps are tracked and validates the compose file.

## Never backed up to GitHub
`.env`, resumes, DB dumps, screenshots, TLS keys, secrets.

## Restore
```bash
# DB restore from a dump
gunzip -c backups/jobagent_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## Application data retention
Job data archived after 365 days (Phase 6 retention job).
