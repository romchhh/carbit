from __future__ import annotations

import logging

from app.core.config import settings
from app.core.redis import get_redis
from app.core.timezone import now_kyiv
from app.services.backup.service import run_backup_and_notify

logger = logging.getLogger(__name__)

_DAILY_KEY_PREFIX = "db_backup:sent:"


async def run_db_backup_if_due() -> None:
    if not settings.DB_BACKUP_ENABLED:
        return

    now = now_kyiv()
    target_hour = int(settings.DB_BACKUP_HOUR_KYIV)
    if now.hour != target_hour or now.minute > 15:
        return

    date_key = now.strftime("%Y-%m-%d")
    marker = f"{_DAILY_KEY_PREFIX}{date_key}"
    try:
        redis = await get_redis()
        if await redis.get(marker):
            return
        await redis.setex(marker, 60 * 60 * 36, "1")
    except Exception:
        logger.debug("Backup dedupe check failed", exc_info=True)

    logger.info("Starting scheduled database backup")
    result = await run_backup_and_notify(manual=False)
    if not result.ok:
        logger.warning("Scheduled backup finished with errors: %s", result.errors)
