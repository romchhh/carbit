from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from app.core.database import AsyncSessionLocal
from app.core.config import settings as app_settings
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters, SourceStatusOut
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.errors import raise_auto_ria_http
from app.services.auto_ria.mapper import sort_listings
from app.services.auto_ria.preview_limits import clamp_preview_request, consume_preview_quota, is_preview_mode
from app.services.auto_ria.service import collect_auto_ria_ids, hydrate_auto_ria_ids
from app.services.fx_rates import refresh_process_rates
from app.services.listings.duplicates import mark_duplicates_in_pool
from app.services.listings.sanitize import sanitize_paginated_listings, slim_listing_for_list
from app.services.olx.errors import OlxError, raise_olx_http
from app.services.olx.service import search_olx
from app.services.parser.runner import ingest_preview_results
from app.services.rate_limit import enforce_rate_limit
from app.services.search.concurrency import acquire_live_search_slot
from app.services.search.pool_cache import (
    HYDRATE_BATCH_SIZE,
    LIVE_POOL_SIZE,
    get_live_pool,
    pool_display_total,
    set_live_pool,
    slice_pool,
)
from app.services.telegram_channels.ingest import search_telegram_listings

logger = logging.getLogger(__name__)

LIVE_SEARCH_CACHE_TTL_SECONDS = 60
OLX_TIMEOUT = 12.0
TELEGRAM_TIMEOUT = 12.0
# Скільки рядків TG сканувати під live-сторінку (не 3000)
TG_LIVE_MAX_SCAN = 400


async def _safe_rate_limits(*, user_id: str, mode: str, page: int) -> None:
    if not is_preview_mode(mode):
        return
    try:
        await enforce_rate_limit(
            key=f"live-search:{user_id}",
            limit=60,
            window_seconds=3600,
            detail="Ліміт пошуків на годину вичерпано. Спробуйте пізніше.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Live search rate-limit failed — continuing without limit")

    if page != 1:
        return
    try:
        await consume_preview_quota(user_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Preview quota failed — continuing without quota")


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


def _pool_items(pool: dict) -> list[ListingOut]:
    return [ListingOut.model_validate(row) for row in (pool.get("items") or [])]


def _pool_pending_ria(pool: dict) -> list[str]:
    return [str(x).strip() for x in (pool.get("pending_ria_ids") or []) if str(x).strip()]


def _merge_into_items(items: list[ListingOut], batch: list[ListingOut], sort_by: str) -> list[ListingOut]:
    if not batch:
        return items
    seen = {item.id for item in items}
    for row in batch:
        if row.id in seen:
            continue
        items.append(row)
        seen.add(row.id)
    items = sort_listings(items, sort_by)
    return mark_duplicates_in_pool(items)


def _refresh_source_counts(pool: dict, items: list[ListingOut], sources: list[SourceStatusOut]) -> None:
    ria_n = sum(1 for i in items if i.source == "auto_ria") + len(_pool_pending_ria(pool))
    olx_n = max(int(pool.get("olx_fetched") or 0), int(pool.get("olx_total") or 0))
    tg_n = max(int(pool.get("tg_fetched") or 0), int(pool.get("tg_total") or 0))
    for src in sources:
        if src.source == "AUTO.RIA":
            src.item_count = ria_n
        elif src.source == "OLX":
            src.item_count = olx_n
        elif src.source == "Telegram":
            src.item_count = tg_n


def _recompute_market_total(pool: dict) -> int:
    ria = max(
        int(pool.get("market_ria") or 0),
        len(_pool_pending_ria(pool)) + int(pool.get("ria_fetched") or 0),
    )
    olx = int(pool.get("olx_total") or pool.get("olx_fetched") or 0)
    tg = int(pool.get("tg_total") or pool.get("tg_fetched") or 0)
    if not pool.get("olx_exhausted", True):
        olx = max(olx, int(pool.get("olx_fetched") or 0) + HYDRATE_BATCH_SIZE)
    if not pool.get("tg_exhausted", True):
        tg = max(tg, int(pool.get("tg_fetched") or 0) + HYDRATE_BATCH_SIZE)
    return ria + olx + tg


async def _fetch_olx_batch(
    filters: SearchFilters,
    *,
    page: int,
    sort_by: str,
) -> tuple[list[ListingOut], bool]:
    """Повертає (items, exhausted). lean=1 HTML page, без folk-варіантів."""
    try:
        result = await asyncio.wait_for(
            search_olx(
                filters,
                page=page,
                per_page=HYDRATE_BATCH_SIZE,
                sort_by=sort_by,
                use_cache=True,
                cache_ttl_seconds=LIVE_SEARCH_CACHE_TTL_SECONDS,
                lean=True,
            ),
            timeout=OLX_TIMEOUT,
        )
        items = list(result.items)
        exhausted = len(items) < HYDRATE_BATCH_SIZE
        return items, exhausted
    except asyncio.TimeoutError:
        logger.warning("lazy OLX timeout page=%s", page)
        return [], True
    except OlxError as exc:
        logger.warning("lazy OLX error page=%s: %s", page, exc)
        return [], True
    except Exception:
        logger.exception("lazy OLX failed page=%s", page)
        return [], True


async def _fetch_tg_batch(
    filters: SearchFilters,
    *,
    page: int,
    sort_by: str,
) -> tuple[list[ListingOut], int, bool]:
    """Повертає (items, total_hint, exhausted)."""
    try:
        async with AsyncSessionLocal() as session:
            result = await asyncio.wait_for(
                search_telegram_listings(
                    session,
                    filters,
                    page=page,
                    per_page=HYDRATE_BATCH_SIZE,
                    sort_by=sort_by,
                    max_scan=min(TG_LIVE_MAX_SCAN, page * HYDRATE_BATCH_SIZE * 15 + 50),
                    keyword_refresh=(page == 1),
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
        items = list(result.items)
        exhausted = len(items) < HYDRATE_BATCH_SIZE
        return items, int(result.total or 0), exhausted
    except asyncio.TimeoutError:
        logger.warning("lazy Telegram timeout page=%s", page)
        return [], 0, True
    except Exception:
        logger.exception("lazy Telegram failed page=%s", page)
        return [], 0, True


async def _ensure_pool_hydrated(
    pool: dict,
    *,
    filters: SearchFilters,
    sort_by: str,
    page: int,
    per_page: int,
) -> dict:
    """Підтягує батчі по 10 з усіх джерел під видиму сторінку."""
    items = _pool_items(pool)
    pending_ria = _pool_pending_ria(pool)
    page = max(int(page), 1)
    per_page = max(int(per_page), 1)
    target = page * per_page

    ria_fetched = int(pool.get("ria_fetched") or 0)
    olx_fetched = int(pool.get("olx_fetched") or 0)
    olx_next = int(pool.get("olx_next_page") or 1)
    olx_exhausted = bool(pool.get("olx_exhausted", False))
    olx_total = int(pool.get("olx_total") or 0)

    tg_enabled = bool(pool.get("tg_enabled", False))
    tg_fetched = int(pool.get("tg_fetched") or 0)
    tg_next = int(pool.get("tg_next_page") or 1)
    tg_exhausted = bool(pool.get("tg_exhausted", not tg_enabled))
    tg_total = int(pool.get("tg_total") or 0)

    # Паралельні батчі лише на fetch; merge в items — послідовно (без гонок).
    async def ria_batch() -> list[ListingOut]:
        nonlocal pending_ria, ria_fetched
        out: list[ListingOut] = []
        while ria_fetched < target and pending_ria:
            batch_ids = pending_ria[:HYDRATE_BATCH_SIZE]
            pending_ria = pending_ria[HYDRATE_BATCH_SIZE:]
            ria_fetched += len(batch_ids)
            try:
                hydrated = await hydrate_auto_ria_ids(batch_ids, sort_by=sort_by)
            except AutoRiaError:
                raise
            except Exception:
                logger.exception("lazy RIA hydrate failed for batch=%s", batch_ids)
                hydrated = []
            out.extend(hydrated)
        return out

    async def olx_batch() -> list[ListingOut]:
        nonlocal olx_fetched, olx_next, olx_exhausted, olx_total
        out: list[ListingOut] = []
        while olx_fetched < target and not olx_exhausted:
            batch, exhausted = await _fetch_olx_batch(filters, page=olx_next, sort_by=sort_by)
            olx_next += 1
            if not batch:
                olx_exhausted = True
                break
            out.extend(batch)
            olx_fetched += len(batch)
            olx_total = max(
                olx_total,
                olx_fetched + (HYDRATE_BATCH_SIZE if not exhausted else 0),
            )
            if exhausted:
                olx_exhausted = True
                break
        return out

    async def tg_batch() -> list[ListingOut]:
        nonlocal tg_fetched, tg_next, tg_exhausted, tg_total
        out: list[ListingOut] = []
        while tg_enabled and tg_fetched < target and not tg_exhausted:
            batch, total_hint, exhausted = await _fetch_tg_batch(
                filters, page=tg_next, sort_by=sort_by
            )
            tg_next += 1
            if total_hint:
                tg_total = max(tg_total, total_hint)
            if not batch:
                tg_exhausted = True
                break
            out.extend(batch)
            tg_fetched += len(batch)
            if exhausted:
                tg_exhausted = True
                break
        return out

    gathered = await asyncio.gather(
        ria_batch(),
        olx_batch(),
        tg_batch(),
        return_exceptions=True,
    )
    for result in gathered:
        if isinstance(result, AutoRiaError):
            raise result
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result
        if isinstance(result, Exception):
            logger.warning("lazy source fill error: %s", result)
            continue
        items = _merge_into_items(items, result, sort_by)

    sources_raw = pool.get("sources") or []
    sources = [SourceStatusOut.model_validate(s) for s in sources_raw]
    pool_state = {
        "items": items,
        "pending_ria_ids": pending_ria,
        "ria_fetched": ria_fetched,
        "olx_next_page": olx_next,
        "olx_fetched": olx_fetched,
        "olx_exhausted": olx_exhausted,
        "olx_total": olx_total,
        "tg_enabled": tg_enabled,
        "tg_next_page": tg_next,
        "tg_fetched": tg_fetched,
        "tg_exhausted": tg_exhausted,
        "tg_total": tg_total,
        "market_ria": int(pool.get("market_ria") or 0),
        "partial": bool(pool.get("partial")),
        "sources": sources,
    }
    pool_state["market_total"] = _recompute_market_total(pool_state)
    _refresh_source_counts(pool_state, items, sources)
    pool_state["sources"] = sources
    pool_state["partial"] = any(s.error for s in sources) and (
        ria_fetched > 0 or olx_fetched > 0 or tg_fetched > 0 or bool(pending_ria)
    )

    await set_live_pool(filters, sort_by, pool=pool_state)

    return {
        **pool_state,
        "items": [item.model_dump(mode="json") for item in items],
        "sources": [s.model_dump() for s in sources],
        "total": pool_display_total(
            {
                **pool_state,
                "items": [item.model_dump(mode="json") for item in items],
            }
        ),
    }


def _page_response(
    pool: dict,
    *,
    page: int,
    per_page: int,
    from_cache: bool,
) -> PaginatedListings:
    page_result = slice_pool(pool, page=page, per_page=per_page)
    page_result.from_cache = from_cache
    page_result.total = pool_display_total(pool)
    page_result.pages = (
        (page_result.total + per_page - 1) // per_page if page_result.total else 0
    )
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
) -> PaginatedListings:
    await _safe_rate_limits(user_id=user_id, mode=mode, page=page)
    page, per_page = clamp_preview_request(page=page, per_page=per_page, mode=mode)

    async def hydrate_window(pool: dict) -> dict:
        return await _ensure_pool_hydrated(
            pool,
            filters=filters,
            sort_by=sort_by,
            page=page,
            per_page=per_page,
        )

    cached_pool = await get_live_pool(filters, sort_by)
    if cached_pool is not None:
        try:
            cached_pool = await hydrate_window(cached_pool)
        except AutoRiaError as exc:
            raise_auto_ria_http(exc)
        return _page_response(cached_pool, page=page, per_page=per_page, from_cache=True)

    async with acquire_live_search_slot():
        cached_pool = await get_live_pool(filters, sort_by)
        if cached_pool is not None:
            try:
                cached_pool = await hydrate_window(cached_pool)
            except AutoRiaError as exc:
                raise_auto_ria_http(exc)
            return _page_response(cached_pool, page=page, per_page=per_page, from_cache=True)

        try:
            # Cold: тільки RIA ids; OLX/TG підвантажаться в hydrate_window батчами
            include_telegram = bool(app_settings.TELEGRAM_ENABLED)
            ria_ids, ria_total = await collect_auto_ria_ids(filters, max_ids=LIVE_POOL_SIZE)
            sources = [
                SourceStatusOut(source="AUTO.RIA", item_count=len(ria_ids), error=None),
                SourceStatusOut(source="OLX", item_count=0, error=None),
            ]
            if include_telegram:
                sources.append(SourceStatusOut(source="Telegram", item_count=0, error=None))

            pool = {
                "items": [],
                "pending_ria_ids": ria_ids,
                "ria_fetched": 0,
                "olx_next_page": 1,
                "olx_fetched": 0,
                "olx_exhausted": False,
                "olx_total": 0,
                "tg_enabled": include_telegram,
                "tg_next_page": 1,
                "tg_fetched": 0,
                "tg_exhausted": not include_telegram,
                "tg_total": 0,
                "market_ria": ria_total,
                "market_total": ria_total,
                "partial": False,
                "sources": [s.model_dump() for s in sources],
            }
            await set_live_pool(filters, sort_by, pool=pool)
            logger.info(
                "live_search cold ria_pending=%s ria_market=%s (OLX/TG deferred)",
                len(ria_ids),
                ria_total,
            )
            pool = await hydrate_window(pool)
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
                "live_search failed user=%s page=%s sort=%s mode=%s",
                user_id,
                page,
                sort_by,
                mode,
            )
            raise HTTPException(
                502,
                "Пошук тимчасово недоступний. Спробуйте ще раз за хвилину.",
            ) from exc

    results = _page_response(pool, page=page, per_page=per_page, from_cache=False)
    logger.info(
        "live_search ok user=%s page=%s shown=%s total=%s ria_f=%s olx_f=%s tg_f=%s",
        user_id,
        page,
        len(results.items),
        results.total,
        pool.get("ria_fetched"),
        pool.get("olx_fetched"),
        pool.get("tg_fetched"),
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
