#!/bin/sh
# ============================================================
# Runs DB migrations + admin seed ONCE (only where RUN_MIGRATIONS=true,
# i.e. the api container), then execs the given command.
# The worker container starts without migrating to avoid a race.
# ============================================================
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "[entrypoint] applying migrations..."
  alembic upgrade head
  echo "[entrypoint] seeding admin user..."
  python -m app.seed
fi

exec "$@"
