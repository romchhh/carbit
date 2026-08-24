from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.monitoring.alerts import run_daily_report_if_due, run_monitoring_tick

logger = logging.getLogger(__name__)


async def monitoring_loop() -> None:
    await asyncio.sleep(20)
    while True:
        try:
            await run_monitoring_tick()
            await run_daily_report_if_due()
        except Exception:
            logger.exception("Monitoring loop tick failed")
        await asyncio.sleep(max(60, int(settings.MONITOR_CHECK_INTERVAL_SECONDS)))
