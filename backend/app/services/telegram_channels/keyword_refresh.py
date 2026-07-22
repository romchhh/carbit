"""Паралельний keyword-scan історії Telegram-каналів під час live-пошуку."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings as app_settings
from app.schemas.schemas import SearchFilters
from app.services.search.brand_model_keywords import (
    MAX_TELEGRAM_KEYWORD_QUERIES,
    TELEGRAM_HISTORY_SCAN_LIMIT,
    TELEGRAM_SCAN_QUERY_PREFIX,
    build_search_keyword_queries,
    encode_telegram_scan_job,
)
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.service_loader import get_parser_channels

logger = logging.getLogger(__name__)

# Telethon search — швидко знаходить і старі пости (не лише останні N).
TELEGRAM_SEARCH_LIMIT = 80
KEYWORD_LIMIT_PER_CHANNEL = TELEGRAM_HISTORY_SCAN_LIMIT
KEYWORD_WAIT_SECONDS = 6.0
KEYWORD_COOLDOWN_SECONDS = 90
# Старі pending scan-и (Tesla тощо) блокували live-пошук годинами.
STALE_JOB_SECONDS = 20 * 60


def build_telegram_keyword_queries(
    filters: SearchFilters,
    *,
    include_history_scan: bool = False,
) -> list[str]:
    """Запити для worker: спочатку plain Telethon search, опційно повний scan."""
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if not brand and not model:
        return []

    seen: set[str] = set()
    out: list[str] = []

    def add(q: str) -> None:
        key = (q or "").strip()
        if not key or key in seen:
            return
        seen.add(key)
        out.append(key)

    # Спочатку швидкий server-side search — покриває пости глибше за limit історії.
    for q in build_search_keyword_queries(brand, model, max_queries=MAX_TELEGRAM_KEYWORD_QUERIES):
        add(q)
    if include_history_scan:
        add(encode_telegram_scan_job(brand, model))
    return out[: MAX_TELEGRAM_KEYWORD_QUERIES + (1 if include_history_scan else 0)]


def build_telegram_keyword_query(filters: SearchFilters) -> str | None:
    """Scan-job payload (brand/model) для worker."""
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if not brand and not model:
        return None
    return encode_telegram_scan_job(brand, model)


def _job_limit_for_query(query: str) -> int:
    if (query or "").startswith(TELEGRAM_SCAN_QUERY_PREFIX):
        return KEYWORD_LIMIT_PER_CHANNEL
    return TELEGRAM_SEARCH_LIMIT


async def refresh_telegram_by_keywords(
    filters: SearchFilters,
    *,
    wait_seconds: float = KEYWORD_WAIT_SECONDS,
    force_rescan: bool = False,
    include_history_scan: bool = False,
) -> int:
    """
    Ставить у чергу Telethon search (+ опційно scan історії) по каналах.
    Worker індексує знайдене в listings — далі йде звичайний DB-пошук.
    """
    if not app_settings.TELEGRAM_ENABLED:
        return 0

    queries = build_telegram_keyword_queries(
        filters,
        include_history_scan=include_history_scan,
    )
    if not queries:
        return 0

    channels = await get_parser_channels()
    if not channels:
        return 0

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    store = ChannelMediaStore()
    # Чистимо застряглі 'running' (воркер впав не завершивши job).
    stuck = store.reset_stuck_running_jobs(older_than_seconds=120)
    if stuck:
        logger.info("Reset %s stuck running keyword jobs", stuck)
    # Прибираємо «мертву» чергу, щоб новий пошук не чекав Tesla-scan з минулої години.
    cancelled = store.cancel_stale_keyword_jobs(older_than_seconds=STALE_JOB_SECONDS)
    if cancelled:
        logger.info("Cancelled %s stale Telegram keyword jobs", cancelled)

    job_ids: list[int] = []
    for query in queries:
        job_ids.extend(
            store.enqueue_keyword_searches(
                query,
                channels,
                limit=_job_limit_for_query(query),
                cooldown_seconds=KEYWORD_COOLDOWN_SECONDS,
                skip_cooldown=force_rescan,
            )
        )
    if not job_ids:
        return 0

    worker_online = False
    try:
        from app.services.health import heartbeat_age_seconds

        age = await heartbeat_age_seconds("telegram_worker")
        worker_online = age is not None and age <= 45
    except Exception:
        logger.debug("Telegram worker heartbeat check failed", exc_info=True)

    if not worker_online:
        logger.warning(
            "Telegram keyword jobs queued brand=%r model=%r jobs=%s "
            "(worker offline — inline Telethon fallback)",
            filters.brand,
            filters.model,
            len(job_ids),
        )
        try:
            from app.services.telegram_channels.keyword_jobs import run_inline_keyword_refresh

            await run_inline_keyword_refresh(job_ids, wait_seconds=max(wait_seconds, 12.0))
        except Exception:
            logger.exception("Inline Telegram keyword refresh failed")
        return len(job_ids)

    if not store.keyword_jobs_pending(job_ids):
        return len(job_ids)

    deadline = time.monotonic() + max(0.5, float(wait_seconds))
    while time.monotonic() < deadline:
        if not store.keyword_jobs_pending(job_ids):
            logger.info(
                "Telegram keyword search ready brand=%r model=%r jobs=%s",
                filters.brand,
                filters.model,
                len(job_ids),
            )
            return len(job_ids)
        await asyncio.sleep(0.35)

    logger.info(
        "Telegram keyword search timeout brand=%r model=%r jobs=%s (worker ще обробляє)",
        filters.brand,
        filters.model,
        len(job_ids),
    )
    return len(job_ids)
