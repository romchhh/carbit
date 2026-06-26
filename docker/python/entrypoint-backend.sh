#!/bin/sh
set -e

mkdir -p /app/database

cd /app/backend
echo "→ Running database migrations..."
alembic upgrade head

echo "→ Starting backend..."
cd /app/backend
exec "$@"
