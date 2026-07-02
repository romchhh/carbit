#!/usr/bin/env bash
# Production deploy without --no-cache (uses BuildKit cache safely).
# Usage: ./scripts/docker-deploy.sh [services...]
# Example: ./scripts/docker-deploy.sh
#          ./scripts/docker-deploy.sh frontend
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

services=("$@")

echo "Pulling latest code..."
git pull

if ((${#services[@]})); then
  echo "Building: ${services[*]}"
  docker compose build "${services[@]}"
  docker compose up -d "${services[@]}"
else
  echo "Building all services..."
  docker compose build
  docker compose up -d
fi

docker compose ps
echo
echo "Build cache usage:"
docker builder du 2>/dev/null || true
