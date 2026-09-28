#!/usr/bin/env python3
"""Ручний бекап БД + Telegram адмінам.

  cd backend && python scripts/run_db_backup.py
  docker compose exec worker python /app/backend/scripts/run_db_backup.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.backup.service import run_backup_and_notify  # noqa: E402


async def main() -> int:
    result = await run_backup_and_notify(manual=True)
    print("ok:", result.ok)
    print("files:", result.files)
    if result.errors:
        print("errors:", result.errors)
    print("source:", result.source)
    print("duration:", f"{result.duration_seconds:.1f}s")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
