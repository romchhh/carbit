from __future__ import annotations

import asyncio
import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
from app.services.auto_ria.mapper import filters_to_search_params, info_to_listing, sort_listings
from app.services.search.concurrency import acquire_auto_ria_slot


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


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

    async def fetch_one(auto_id: str) -> ListingOut | None:
        async with sem:
            try:
                info_task = client.get_info(auto_id)
                fotos_task = client.get_fotos(auto_id)
                info, fotos_result = await asyncio.gather(info_task, fotos_task, return_exceptions=True)
                if isinstance(info, BaseException):
                    return None
                fotos = None if isinstance(fotos_result, BaseException) else fotos_result
                return info_to_listing(info, fotos=fotos)
            except AutoRiaError:
                return None

    listings = [item for item in await asyncio.gather(*(fetch_one(aid) for aid in auto_ids)) if item]
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
