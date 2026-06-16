#!/usr/bin/env bash
# ============================================================
# job-agent — daily GitHub backup of CODE / INFRA / CONFIG drift
# Commits and pushes tracked changes only. .gitignore guarantees
# secrets, resumes, DB dumps, and screenshots are NEVER pushed.
# Schedule via cron, e.g.:  0 3 * * * /opt/job-agent/scripts/github-backup.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

BRANCH="${BACKUP_BRANCH:-main}"

# Safety: refuse to run if sensitive files are somehow staged
if git status --porcelain | grep -E '(^|/)\.env($|\.)|resumes/|\.sql\.gz|secrets/' >/dev/null; then
  echo "[github-backup] ERROR: sensitive files detected in working tree. Aborting."
  exit 1
fi

git add -A

if git diff --cached --quiet; then
  echo "[github-backup] no changes to back up."
  exit 0
fi

STAMP="$(date +%Y-%m-%d\ %H:%M:%S)"
git commit -m "chore(backup): infra/config drift ${STAMP}"

# Uses GITHUB_TOKEN from .env for non-interactive push (token never committed)
git push "https://${GITHUB_TOKEN}@${GITHUB_REPO#https://}" "${BRANCH}"

echo "[github-backup] pushed to ${GITHUB_REPO} (${BRANCH})."
