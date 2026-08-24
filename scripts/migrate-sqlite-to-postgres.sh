#!/bin/sh
# Імпорт database/autoradar.db → PostgreSQL (всередині Docker backend).
set -e
cd "$(dirname "$0")/.."

echo "→ SQLite → PostgreSQL migration"
docker compose exec backend python /app/backend/scripts/migrate_sqlite_to_postgres.py "$@"
