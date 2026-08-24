#!/usr/bin/env python3
"""CLI: діагностика та імпорт SQLite → PostgreSQL.

Docker:
  docker compose exec backend python /app/backend/scripts/migrate_sqlite_to_postgres.py --status
  docker compose exec backend python /app/backend/scripts/migrate_sqlite_to_postgres.py --force
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.sqlite_to_postgres import (  # noqa: E402
    MigrationStatus,
    migrate_sqlite_to_postgres,
    migration_status_report,
)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Import autoradar.db into PostgreSQL")
    parser.add_argument("--status", action="store_true", help="Show counts and paths only")
    parser.add_argument("--force", action="store_true", help="Merge even if postgres has data")
    args = parser.parse_args()

    if args.status:
        await migration_status_report()
        return 0

    result = await migrate_sqlite_to_postgres(force=args.force)
    result.log()
    if result.status == MigrationStatus.FAILED:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
