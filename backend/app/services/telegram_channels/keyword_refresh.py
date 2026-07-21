"""Паралельний keyword-scan історії Telegram-каналів під час live-пошуку."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings as app_settings
from app.schemas.schemas import SearchFilters
from app.services.search.brand_model_keywords import (
    TELEGRAM_HISTORY_SCAN_LIMIT,
    encode_telegram_scan_job,
)
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.service_loader import get_parser_channels

logger = logging.getLogger(__name__)

KEYWORD_LIMIT_PER_CHANNEL = TELEGRAM_HISTORY_SCAN_LIMIT
# Коротка пауза, щоб worker встиг проіндексувати збіги до відповіді пошуку.
KEYWORD_WAIT_SECONDS = 4.0
KEYWORD_COOLDOWN_SECONDS = 90


def build_telegram_keyword_query(filters: SearchFilters) -> str | None:
    """Scan-job payload (brand/model) для worker."""
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if not brand and not model:
        return None
    return encode_telegram_scan_job(brand, model)


async def refresh_telegram_by_keywords(
    filters: SearchFilters,
    *,
    wait_seconds: float = KEYWORD_WAIT_SECONDS,
) -> int:
    """
    Ставить у чергу scan історії по всіх увімкнених каналах (variant matching).
    Worker індексує знайдене в listings — далі йде звичайний DB-пошук.
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
                "Telegram history scan queued brand=%r model=%r (worker offline/stale, no wait)",
                filters.brand,
                filters.model,
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
                "Telegram history scan ready brand=%r model=%r jobs=%s",
                filters.brand,
                filters.model,
                len(job_ids),
            )
            return len(job_ids)
        await asyncio.sleep(0.35)

    logger.info(
        "Telegram history scan timeout brand=%r model=%r jobs=%s (worker ще обробляє)",
        filters.brand,
        filters.model,
        len(job_ids),
    )
    return len(job_ids)
