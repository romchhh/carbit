#!/usr/bin/env python3
"""Фоновий worker: черга parse jobs + періодичний парсинг збережених пошуків."""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.timezone import now_kyiv  # noqa: E402
from app.models.models import ParseRun, ParseRunStatus  # noqa: E402
from app.services.health import beat  # noqa: E402
from app.services.parser.queue import (  # noqa: E402
    STALE_RUNNING_SECONDS,
    acquire_cycle_lock,
    pop_parse_jobs,
    release_cycle_lock,
)
from app.services.parser.runner import run_parser_cycle, run_parser_for_search  # noqa: E402
from app.services.parser.settings import get_parser_settings  # noqa: E402
from app.services.billing.maintenance import run_billing_maintenance  # noqa: E402
from sqlalchemy import select  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
logger = logging.getLogger("carbit.worker")


async def mark_stale_runs() -> None:
    cutoff = now_kyiv() - timedelta(seconds=STALE_RUNNING_SECONDS)
    async with AsyncSessionLocal() as db:
        rows = await db.scalars(
            select(ParseRun).where(
                ParseRun.status == ParseRunStatus.running,
                ParseRun.started_at < cutoff,
            )
        )
        stale = list(rows.all())
        for run in stale:
            run.status = ParseRunStatus.failed
            run.error = "Stale running parse (worker crash or timeout)"
            run.finished_at = now_kyiv()
            log = list(run.log or [])
            log.append("Позначено як failed: завислий running")
            run.log = log
        if stale:
            await db.commit()
            logger.warning("Marked %s stale ParseRun(s) as failed", len(stale))


async def drain_jobs() -> None:
    jobs = await pop_parse_jobs(limit=20)
    for job in jobs:
        search_id = job.get("search_id")
        if not search_id:
            continue
        async with AsyncSessionLocal() as db:
            try:
                await run_parser_for_search(db, search_id)
                from app.services.notifications.service import deliver_pending_monitor_telegram

                await deliver_pending_monitor_telegram(db, search_ids=[search_id], limit=30)
                await db.commit()
                logger.info("Processed parse job for search %s", search_id)
            except Exception:
                await db.rollback()
                logger.exception("Parse job failed for search %s", search_id)


async def run_billing_once() -> None:
    async with AsyncSessionLocal() as db:
        try:
            result = await run_billing_maintenance(db)
            await db.commit()
            if result.get("skipped"):
                logger.info("Billing maintenance skipped (%s)", result.get("reason"))
            else:
                logger.info(
                    "Billing maintenance: expired=%s past_due=%s",
                    result.get("expired_plans"),
                    result.get("past_due_cancelled"),
                )
        except Exception:
            await db.rollback()
            logger.exception("Billing maintenance failed")


async def run_once() -> None:
    owner = f"worker-{uuid.uuid4().hex[:8]}"
    if not await acquire_cycle_lock(owner):
        logger.info("Cycle lock held — skipping scheduler cycle")
        return
    try:
        await mark_stale_runs()
        await drain_jobs()
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
    finally:
        await release_cycle_lock(owner)


async def main() -> None:
    logger.info("Carbit parser worker started")
    while True:
        await beat("worker")
        settings = await get_parser_settings()
        interval = int(settings.get("interval_seconds", 900))
        try:
            await run_billing_once()
        except Exception:
            logger.exception("Billing tick failed")
        try:
            await run_once()
        except Exception:
            logger.exception("Parser cycle failed")
        await beat("worker")
        logger.info("Sleeping %s seconds", interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
