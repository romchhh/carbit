"""Паралельний keyword-scan історії Telegram-каналів під час live-пошуку."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings as app_settings
from app.schemas.schemas import SearchFilters
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.service_loader import get_parser_channels

logger = logging.getLogger(__name__)

KEYWORD_LIMIT_PER_CHANNEL = 40
KEYWORD_WAIT_SECONDS = 8.0
KEYWORD_COOLDOWN_SECONDS = 120


def build_telegram_keyword_query(filters: SearchFilters) -> str | None:
    parts: list[str] = []
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if brand:
        parts.append(brand)
    if model:
        parts.append(model)
    query = " ".join(parts).strip()
    return query or None


async def refresh_telegram_by_keywords(
    filters: SearchFilters,
    *,
    wait_seconds: float = KEYWORD_WAIT_SECONDS,
) -> int:
    """
    Ставить у чергу keyword-пошук по всіх увімкнених каналах і чекає worker
    (коротко). Worker індексує знайдене в listings — далі йде звичайний DB-пошук.
    """
    if not app_settings.TELEGRAM_ENABLED:
        return 0

    query = build_telegram_keyword_query(filters)
    if not query:
        return 0

    channels = await get_parser_channels()
    if not channels:
        return 0

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    store = ChannelMediaStore()
    job_ids = store.enqueue_keyword_searches(
        query,
        channels,
        limit=KEYWORD_LIMIT_PER_CHANNEL,
        cooldown_seconds=KEYWORD_COOLDOWN_SECONDS,
    )
    if not job_ids:
        return 0

    # Немає живого worker — лише ставимо в чергу, не блокуємо live-пошук.
    try:
        from app.services.health import heartbeat_age_seconds

        age = await heartbeat_age_seconds("telegram_worker")
        if age is None or age > 45:
            logger.info(
                "Telegram keyword jobs queued q=%r (worker offline/stale, no wait)",
                query,
            )
            return len(job_ids)
    except Exception:
        logger.debug("Telegram worker heartbeat check failed", exc_info=True)

    if not store.keyword_jobs_pending(job_ids):
        return len(job_ids)

    deadline = time.monotonic() + max(0.5, float(wait_seconds))
    while time.monotonic() < deadline:
        if not store.keyword_jobs_pending(job_ids):
            logger.info(
                "Telegram keyword search ready q=%r jobs=%s",
                query,
                len(job_ids),
            )
            return len(job_ids)
        await asyncio.sleep(0.35)

    logger.info(
        "Telegram keyword search timeout q=%r jobs=%s (worker ще обробляє)",
        query,
        len(job_ids),
    )
    return len(job_ids)
