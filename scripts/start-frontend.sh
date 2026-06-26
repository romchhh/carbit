#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

if [ ! -f "$ROOT/.env" ]; then
  echo "→ Copy .env.example → .env and configure it"
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

# shellcheck disable=SC1091
source "$ROOT/scripts/load-env.sh"

if [ ! -d "node_modules" ]; then
  echo "→ Installing dependencies..."
  npm install
fi

echo "→ Starting frontend on http://localhost:3000"
exec npm run dev
