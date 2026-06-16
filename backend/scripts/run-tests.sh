#!/usr/bin/env bash
# ============================================================
# Phase 4A — run the API validation suite inside the api container.
# Requires the stack to be up (docker compose up -d) with TEST_MODE=true.
# Usage (from repo root):  docker compose exec api ./scripts/run-tests.sh
# ============================================================
set -euo pipefail

echo "[tests] installing dev deps..."
pip install -q -r requirements-dev.txt

echo "[tests] seeding demo data..."
python -m app.seed_demo || true

echo "[tests] running pytest..."
API_BASE="${API_BASE:-http://localhost:8000}" pytest
