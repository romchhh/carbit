from __future__ import annotations

import asyncio
import json
import logging

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria import detail_cache
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
from app.services.auto_ria.mapper import filters_to_search_params, sort_listings
from app.services.search.concurrency import acquire_auto_ria_slot

logger = logging.getLogger(__name__)

# AUTO.RIA countpage ≤ 50
AUTO_RIA_SEARCH_PAGE = 50


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def collect_auto_ria_ids(
    filters: SearchFilters,
    *,
    max_ids: int = 120,
) -> tuple[list[str], int]:
    """Лише /auto/search — без get_info. Дешево по API-квоті."""
    max_ids = max(int(max_ids), 0)
    if max_ids == 0:
        return [], 0

    async with acquire_auto_ria_slot():
        client = AutoRiaClient()
        collected: list[str] = []
        seen: set[str] = set()
        total = 0
        page = 1
        max_pages = min(max((max_ids + AUTO_RIA_SEARCH_PAGE - 1) // AUTO_RIA_SEARCH_PAGE, 1), 6)

        while len(collected) < max_ids and page <= max_pages:
            try:
                params = await filters_to_search_params(
                    client,
                    filters,
                    page=page,
                    per_page=min(AUTO_RIA_SEARCH_PAGE, max_ids - len(collected)),
                )
                search_data = await client.search(params)
            except ValueError as exc:
                raise AutoRiaError(str(exc)) from exc

            search_result = (search_data.get("result") or {}).get("search_result") or {}
            total = max(total, int(search_result.get("count") or 0))
            raw_ids = search_result.get("ids") or []
            if not raw_ids:
                break
            for raw in raw_ids:
                aid = str(raw).strip()
                if not aid or aid in seen:
                    continue
                seen.add(aid)
                collected.append(aid)
                if len(collected) >= max_ids:
                    break
            if page * AUTO_RIA_SEARCH_PAGE >= total:
                break
            page += 1

        logger.info(
            "auto_ria ids collected=%s market_total=%s pages=%s",
            len(collected),
            total,
            page,
        )
        return collected, total


async def hydrate_auto_ria_ids(
    auto_ids: list[str],
    *,
    sort_by: str = "newest",
) -> list[ListingOut]:
    """get_info лише для переданих ID (батч видимих карток)."""
    ids = [str(a).strip() for a in auto_ids if str(a).strip()]
    if not ids:
        return []

    async with acquire_auto_ria_slot():
        client = AutoRiaClient()
        sem = asyncio.Semaphore(4)

        async def fetch_info(auto_id: str):
            async with sem:
                return await client.get_info(auto_id)

        listings = await detail_cache.resolve_listings(ids, fetch_info=fetch_info)
        return sort_listings(listings, sort_by)


async def _search_auto_ria_uncached(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    async with acquire_auto_ria_slot():
        return await _search_auto_ria_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )


async def _search_auto_ria_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = AutoRiaClient()

    try:
        params = await filters_to_search_params(client, filters, page=page, per_page=per_page)
        search_data = await client.search(params)
    except ValueError as exc:
        raise AutoRiaError(str(exc)) from exc

    search_result = (search_data.get("result") or {}).get("search_result") or {}
    total = int(search_result.get("count") or 0)
    raw_ids = search_result.get("ids") or []
    # Не гідратимо більше, ніж потрібно для поточної сторінки/пулу
    auto_ids = [str(item) for item in raw_ids if item][: max(per_page, 0)]

    sem = asyncio.Semaphore(4)

    async def fetch_info(auto_id: str):
        async with sem:
            return await client.get_info(auto_id)

    # KV (14д) → listings у БД з фото → лише miss йде в AUTO.RIA API
    listings = await detail_cache.resolve_listings(auto_ids, fetch_info=fetch_info)
    listings = sort_listings(listings, sort_by)

    pages = (total + per_page - 1) // per_page if total else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def search_auto_ria(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_auto_ria_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )

    key = _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by)
    is_browse = not filters.model_dump(exclude_none=True)
    ttl = 180 if is_browse else cache_ttl_seconds
    return await get_or_fetch(
        key,
        lambda: _search_auto_ria_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        ),
        ttl_seconds=ttl,
    )
