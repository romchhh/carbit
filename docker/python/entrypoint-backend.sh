#!/bin/sh
set -e

cd /app/backend
echo "→ Running database migrations..."
alembic upgrade head

cd /app/backend
exec "$@"
