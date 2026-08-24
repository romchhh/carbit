#!/bin/sh
set -e

mkdir -p /app/database /app/media

cd /app/backend
echo "→ Running database migrations..."
alembic upgrade head

echo "→ Importing legacy SQLite data into PostgreSQL (if needed)..."
python - <<'PY'
import asyncio
import sys

sys.path.insert(0, "/app/backend")
from app.core.sqlite_to_postgres import MigrationStatus, run_startup_migration

result = asyncio.run(run_startup_migration())
if result.status == MigrationStatus.FAILED:
    raise SystemExit(1)
PY

echo "→ Checking production secrets..."
python - <<'PY'
import os
import sys

sys.path.insert(0, "/app/backend")
from app.core.config import settings
from app.core.secrets_guard import assert_production_secrets

print(
    f"  DEBUG={settings.DEBUG} FRONTEND_URL={settings.FRONTEND_URL!r} "
    f"REDIS_URL={settings.REDIS_URL!r} "
    f"SECRET_KEY_len={len(settings.SECRET_KEY)} "
    f"INTERNAL_len={len(settings.INTERNAL_API_SECRET)} "
    f"ADMIN_PASS_len={len(settings.ADMIN_PASSWORD)}"
)
try:
    assert_production_secrets(
        debug=settings.DEBUG,
        secret_key=settings.SECRET_KEY,
        internal_api_secret=settings.INTERNAL_API_SECRET,
        admin_password=settings.ADMIN_PASSWORD,
        frontend_url=settings.FRONTEND_URL,
    )
except RuntimeError as exc:
    print("FATAL: backend will not start until .env secrets are fixed:", file=sys.stderr)
    print(f"  {exc}", file=sys.stderr)
    print(
        "  Generate: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"",
        file=sys.stderr,
    )
    print(
        "  Set SECRET_KEY, INTERNAL_API_SECRET, ADMIN_PASSWORD (>=10 chars). DEBUG=false on prod.",
        file=sys.stderr,
    )
    raise SystemExit(1)
print("  secrets: ok")
PY

WORKERS="${UVICORN_WORKERS:-1}"
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

echo "→ Starting backend (workers=$WORKERS, REDIS_URL=${REDIS_URL:-unset})..."
cd /app/backend
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "$WORKERS"
