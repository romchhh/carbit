"""Паралельний keyword-scan історії Telegram-каналів під час live-пошуку."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings as app_settings
from app.core.text import norm_text
from app.schemas.schemas import SearchFilters
from app.services.search.brand_model_keywords import (
    TELEGRAM_HISTORY_SCAN_LIMIT,
    TELEGRAM_SCAN_QUERY_PREFIX,
    build_search_keyword_queries,
    collect_brand_keyword_variants,
    collect_model_keyword_variants,
    encode_telegram_scan_job,
    _allows_distinctive_model_without_brand,
)
from app.services.telegram_channels.bootstrap import ensure_parser_path
from app.services.telegram_channels.service_loader import get_parser_channels

logger = logging.getLogger(__name__)

# Telethon search — швидко знаходить пости глибше за повзунок історії.
TELEGRAM_SEARCH_LIMIT = 250
KEYWORD_LIMIT_PER_CHANNEL = TELEGRAM_HISTORY_SCAN_LIMIT
# Мало запитів × канали: інакше черга 200+ джобів і Countryman не встигає.
KEYWORD_WAIT_SECONDS = 25.0
KEYWORD_COOLDOWN_SECONDS = 45
STALE_JOB_SECONDS = 20 * 60
THIN_RESULT_RETRY_THRESHOLD = 15
THIN_RETRY_WAIT_SECONDS = 40.0
# Жорсткий ліміт plain Telethon-запитів (без __scan__).
MAX_LIVE_TELEGRAM_SEARCH_QUERIES = 4


def build_telegram_keyword_queries(
    filters: SearchFilters,
    *,
    include_history_scan: bool = False,
) -> list[str]:
    """Короткий пріоритетний список запитів — щоб worker встиг за wait_seconds."""
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
        # Відсікаємо шум на кшталт «Mini Mini Countryman».
        parts = key.split()
        if len(parts) >= 3 and parts[0].lower() == parts[1].lower():
            return
        seen.add(key)
        out.append(key)

    # 1) Distinctive model без бренду — Telethon часто знаходить саме так.
    if brand and model and _allows_distinctive_model_without_brand(brand, model):
        for mt in collect_model_keyword_variants(brand, model):
            mt_k = norm_text(mt)
            if mt_k and len(mt_k) >= 4 and " " not in mt_k.strip():
                add(mt)
            if len(out) >= 2:
                break
        # також «міні кантрімен» / «Mini Countryman» як цілі фрази нижче

    # 2) Найкращі brand+model (latin + один cyrillic).
    if brand and model:
        primary = build_search_keyword_queries(brand, model, max_queries=6)
        for q in primary:
            qn = norm_text(q)
            # лише фрази з моделлю або короткі distinctive
            if model and norm_text(model).split()[0] not in qn and len(qn) < 4:
                continue
            add(q)
            if len([x for x in out if not x.startswith(TELEGRAM_SCAN_QUERY_PREFIX)]) >= (
                MAX_LIVE_TELEGRAM_SEARCH_QUERIES
            ):
                break

    if not model and brand:
        for bv in collect_brand_keyword_variants(brand)[:2]:
            add(bv)

    if model and not brand:
        for mt in collect_model_keyword_variants("", model)[:2]:
            if len(norm_text(mt)) >= 3:
                add(mt)

    # Обрізаємо plain search
    plain = [q for q in out if not q.startswith(TELEGRAM_SCAN_QUERY_PREFIX)]
    plain = plain[:MAX_LIVE_TELEGRAM_SEARCH_QUERIES]
    out = list(plain)

    if include_history_scan:
        scan = encode_telegram_scan_job(brand, model)
        if scan:
            out.append(scan)

    return out


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
    stuck = store.reset_stuck_running_jobs(older_than_seconds=120)
    if stuck:
        logger.info("Reset %s stuck running keyword jobs", stuck)
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

    logger.info(
        "Telegram keyword enqueue brand=%r model=%r queries=%s channels=%s jobs=%s "
        "history_scan=%s force=%s",
        filters.brand,
        filters.model,
        queries,
        len(channels),
        len(job_ids),
        include_history_scan,
        force_rescan,
    )

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

            await run_inline_keyword_refresh(job_ids, wait_seconds=max(wait_seconds, 20.0))
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
