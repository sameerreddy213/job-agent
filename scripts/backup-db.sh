#!/usr/bin/env bash
# ============================================================
# job-agent — nightly PostgreSQL backup
# Output is written to ./backups which is GIT-IGNORED.
# Dumps are NEVER committed to GitHub.
# Schedule via cron, e.g.:  0 2 * * * /opt/job-agent/scripts/backup-db.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

BACKUP_DIR="./backups"
RETENTION_DAYS="${DB_BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/jobagent_${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[backup-db] dumping database ${POSTGRES_DB}..."
docker compose exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${OUT}"

echo "[backup-db] wrote ${OUT}"

echo "[backup-db] pruning dumps older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name 'jobagent_*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete

echo "[backup-db] done."
