#!/usr/bin/env bash
# ============================================================
# job-agent — deploy on the AWS EC2 host
# Pulls latest code, rebuilds images, restarts the stack.
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[deploy] pulling latest from git..."
git pull --ff-only

echo "[deploy] verifying .env exists..."
if [ ! -f .env ]; then
  echo "[deploy] ERROR: .env missing. Copy .env.example to .env and fill it in."
  exit 1
fi

echo "[deploy] building images..."
docker compose build

echo "[deploy] starting stack..."
docker compose up -d

echo "[deploy] pruning dangling images..."
docker image prune -f

echo "[deploy] done. Status:"
docker compose ps
