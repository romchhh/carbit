#!/usr/bin/env bash
# Завантажує кореневий .env у поточну shell-сесію.
# Використання: source "$ROOT/scripts/load-env.sh"

_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$_ROOT/.env"
  set +a
fi
