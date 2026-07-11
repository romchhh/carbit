#!/bin/sh
set -e

mkdir -p /app/database /app/media

cd /app/backend
echo "→ Running database migrations..."
alembic upgrade head

WORKERS="${UVICORN_WORKERS:-1}"
# SQLite + multiple workers is unsafe; force 1 unless explicitly using Postgres.
case "${DATABASE_URL:-}" in
  postgresql*|postgres*)
    ;;
  *)
    if [ "$WORKERS" != "1" ]; then
      echo "WARNING: UVICORN_WORKERS=$WORKERS with non-Postgres DB — forcing workers=1"
      WORKERS=1
    fi
    ;;
esac

echo "→ Starting backend (workers=$WORKERS)..."
cd /app/backend
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "$WORKERS"
