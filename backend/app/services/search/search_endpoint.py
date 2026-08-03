from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from app.core.database import AsyncSessionLocal
from app.schemas.schemas import PaginatedListings, SearchFilters, SourceStatusOut
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.catalog import model_filter_needs_post_filter
from app.services.auto_ria.errors import raise_auto_ria_http
from app.services.auto_ria.preview_limits import clamp_preview_request, is_preview_mode
from app.services.fx_rates import refresh_process_rates
from app.services.listings.sanitize import sanitize_paginated_listings, slim_listing_for_list
from app.services.olx.errors import OlxError, raise_olx_http
from app.services.parser.runner import ingest_preview_results
from app.services.rate_limit import enforce_rate_limit
from app.services.search.concurrency import acquire_live_search_slot
from app.services.search.multi_source import build_live_search_pool, SourceSearchStatus
from app.services.search.pool_cache import (
    LIVE_POOL_SIZE,
    get_live_pool,
    set_live_pool,
    slice_pool,
)

logger = logging.getLogger(__name__)

LIVE_SEARCH_CACHE_TTL_SECONDS = 120


def _pool_market_total_for_cache(
    *,
    model_post_filter: bool,
    market_total: int,
    nav_total: int,
) -> int | None:
    if model_post_filter:
        return None
    return market_total if market_total > nav_total else None


async def _safe_rate_limits(
    *,
    user_id: str,
    mode: str,
    page: int,
    hourly_limit: int,
) -> None:
    """Ліміт лише на новий пошук (page=1). Пагінація / «Показати ще» не витрачає квоту."""
    if not is_preview_mode(mode):
        return
    if page != 1:
        return
    try:
        await enforce_rate_limit(
            key=f"live-search:{user_id}",
            limit=max(1, hourly_limit),
            window_seconds=3600,
            detail="Ліміт пошуків на годину вичерпано.",
            code="search_rate_limit",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Live search rate-limit failed — continuing without limit")


async def _ingest_preview_background(
    filters: SearchFilters,
    results: PaginatedListings,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await ingest_preview_results(
                db,
                filters,
                results.items,
                total=results.total,
                pages=results.pages,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Failed to ingest preview results")


def _outcome_sources(statuses: list[SourceSearchStatus]) -> list[SourceStatusOut]:
    return [
        SourceStatusOut(
            source=row.source,
            item_count=int(row.item_count or 0),
            error=row.error,
            pending=False,
        )
        for row in (statuses or [])
    ]


async def _page_from_cached_pool(
    cached_pool: dict,
    *,
    page: int,
    per_page: int,
    filters: SearchFilters,
) -> PaginatedListings:
    """Slice a page from the cached slot pool, hydrating AUTO.RIA items on demand."""
    page_result = await slice_pool(cached_pool, page=page, per_page=per_page, filters=filters)
    page_result.items = [slim_listing_for_list(item) for item in page_result.items]
    return sanitize_paginated_listings(page_result)


async def run_live_search(
    filters: SearchFilters,
    *,
    user_id: str,
    page: int,
    per_page: int,
    sort_by: str,
    mode: str,
    hourly_limit: int = 30,
) -> PaginatedListings:
    await _safe_rate_limits(
        user_id=user_id,
        mode=mode,
        page=page,
        hourly_limit=hourly_limit,
    )
    page, per_page = clamp_preview_request(page=page, per_page=per_page, mode=mode)

    # 1) Пул у KV — «Показати ще» без повторних запитів до OLX/AUTO.RIA
    cached_pool = await get_live_pool(filters, sort_by)
    if cached_pool is not None:
        return await _page_from_cached_pool(
            cached_pool, page=page, per_page=per_page, filters=filters
        )

    # 2) Будуємо слот-пул: AUTO.RIA — тільки IDs (швидко), OLX/Telegram — повні об'єкти
    pool_data: dict | None = None

    async with acquire_live_search_slot():
        # Stampede guard: інший запит міг уже заповнити кеш, поки ми чекали слот
        cached_pool = await get_live_pool(filters, sort_by)
        if cached_pool is not None:
            return await _page_from_cached_pool(
                cached_pool, page=page, per_page=per_page, filters=filters
            )

        slots: list[dict] = []
        nav_total = 0
        market_total = 0
        source_statuses: list[SourceSearchStatus] = []
        try:
            slots, nav_total, market_total, source_statuses = await build_live_search_pool(
                filters,
                sort_by=sort_by,
                max_ids=LIVE_POOL_SIZE,
                keyword_refresh=True,
                olx_enrich_details=False,
            )
        except AutoRiaError as exc:
            logger.warning("live_search auto_ria_error user=%s page=%s detail=%s", user_id, page, exc)
            raise_auto_ria_http(exc)
        except OlxError as exc:
            logger.warning("live_search olx_error user=%s page=%s detail=%s", user_id, page, exc)
            raise_olx_http(exc)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "live_search failed user=%s page=%s sort=%s mode=%s", user_id, page, sort_by, mode
            )
            raise HTTPException(
                502,
                "Пошук тимчасово недоступний. Спробуйте ще раз за хвилину.",
            ) from exc

        sources = _outcome_sources(source_statuses)
        partial = any(s.error for s in sources) and any(s.item_count > 0 for s in sources)

        model_post_filter = False
        if (filters.model or "").strip():
            try:
                from app.services.auto_ria.client import AutoRiaClient

                model_post_filter = await model_filter_needs_post_filter(AutoRiaClient(), filters)
            except Exception:
                logger.exception("model_post_filter check failed")

        pool_market_total = _pool_market_total_for_cache(
            model_post_filter=model_post_filter,
            market_total=market_total,
            nav_total=nav_total,
        )

        logger.info(
            "live_search pool_built user=%s page=%s slots=%s market_total=%s partial=%s sources=%s",
            user_id,
            page,
            nav_total,
            market_total,
            partial,
            [(s.source, s.item_count, s.error) for s in sources],
        )

        pool_data = {
            "slots": slots,
            "total": nav_total,
            "market_total": pool_market_total,
            "sources": [s.model_dump() if hasattr(s, "model_dump") else s.__dict__ for s in sources],
            "partial": partial,
            "model_post_filter": model_post_filter,
        }

        await set_live_pool(
            filters,
            sort_by,
            slots=slots,
            total=nav_total,
            market_total=pool_market_total,
            sources=sources,
            partial=partial,
            model_post_filter=model_post_filter,
            ttl_seconds=LIVE_SEARCH_CACHE_TTL_SECONDS,
        )

    # 3) Гідратуємо лише поточну сторінку (10 AUTO.RIA get_info замість 500)
    assert pool_data is not None
    results = await _page_from_cached_pool(
        pool_data, page=page, per_page=per_page, filters=filters
    )

    if page == 1:
        try:
            asyncio.create_task(_ingest_preview_background(filters, results))
        except Exception:
            logger.exception("Failed to schedule preview ingest")
        try:
            asyncio.create_task(refresh_process_rates())
        except Exception:
            pass

    return results
