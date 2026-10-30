"""Запуск: python -m app.services.backup (у Docker worker/backend)."""

from __future__ import annotations

import asyncio
import sys

from app.services.backup.service import run_backup_and_notify


async def _main() -> int:
    result = await run_backup_and_notify(manual=True)
    print("ok:", result.ok)
    print("files:", result.files)
    if result.errors:
        print("errors:", result.errors)
    print("source:", result.source)
    print("duration:", f"{result.duration_seconds:.1f}s")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
