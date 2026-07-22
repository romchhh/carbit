#!/usr/bin/env python3
"""
Авторизація Telethon (user client) у правильній директорії сесії.

Файл сесії: database/<TELETHON_SESSION_NAME>.session (за замовчуванням carbit_parser.session)
Налаштування: TELETHON_API_ID, TELETHON_API_HASH, TELETHON_NUMBER у .env

Локально:
  python auth.py
  python auth.py --reset

Docker (на VPS, інтерактивно):
  docker compose stop telegram-worker
  docker compose run --rm -it -w /app --entrypoint python telegram-worker auth.py --reset
  docker compose up -d telegram-worker
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser.auth import main

if __name__ == "__main__":
    main()
