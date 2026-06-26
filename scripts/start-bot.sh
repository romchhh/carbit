#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

if [ ! -f "$ROOT/.env" ]; then
  echo "→ Copy .env.example → .env and configure it"
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

# shellcheck disable=SC1091
source "$ROOT/scripts/load-env.sh"

if [ ! -d "$VENV" ]; then
  echo "→ Creating virtualenv..."
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install -q -r "$ROOT/requirements.txt"

cd "$ROOT/bot"
echo "→ Starting Telegram bot (long polling)..."
exec python main.py
