#!/usr/bin/env python3
"""Фоновий worker: періодичний парсинг збережених пошуків."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.services.parser.runner import run_parser_cycle  # noqa: E402
from app.services.parser.settings import get_parser_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
logger = logging.getLogger("carbit.worker")


async def run_once() -> None:
    async with AsyncSessionLocal() as db:
        run = await run_parser_cycle(db, triggered_by="scheduler")
        await db.commit()
        logger.info(
            "Cycle %s: found=%s new=%s telegram=%s",
            run.status.value,
            run.listings_found,
            run.listings_new,
            run.notifications_sent,
        )


async def main() -> None:
    logger.info("Carbit parser worker started")
    while True:
        settings = await get_parser_settings()
        interval = int(settings.get("interval_seconds", 900))
        try:
            await run_once()
        except Exception:
            logger.exception("Parser cycle failed")
        logger.info("Sleeping %s seconds", interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
