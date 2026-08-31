from __future__ import annotations

import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.lubeavto.client import LubeAvtoClient
from app.services.lubeavto.constants import (
    DEFAULT_CATALOG,
    LUBEAVTO_MAX_PAGES,
    LUBEAVTO_PAGE_SIZE,
)
from app.services.lubeavto.errors import LubeAvtoError
from app.services.lubeavto.mapper import car_to_listing, filters_to_catalog_path
from app.services.search.filter_multi import effective_brands
from app.services.telegram_channels.mapper import listing_out_matches_filters


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "lubeavto",
        "lubeavto_v": "card-v1",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_lubeavto_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = LubeAvtoClient()
    brand_hint = (effective_brands(filters) or [None])[0]
    catalog_path = filters_to_catalog_path(filters, catalog=DEFAULT_CATALOG)
    page_number = max(page - 1, 0)

    try:
        cars, total = await client.fetch_catalog(
            catalog_path,
            page_number=page_number,
            catalog=DEFAULT_CATALOG,
        )
        if not cars and (filters.brand or filters.brands):
            fallback_path = filters_to_catalog_path(
                filters.model_copy(update={"brand": None, "brands": None, "model": None, "models": None}),
                catalog=DEFAULT_CATALOG,
            )
            cars, total = await client.fetch_catalog(
                fallback_path,
                page_number=page_number,
                catalog=DEFAULT_CATALOG,
            )
    except ValueError as exc:
        raise LubeAvtoError(str(exc)) from exc

    listings: list[ListingOut] = []
    for car in cars:
        listings.append(car_to_listing(car, brand_hint=brand_hint))

    listings = [item for item in listings if listing_out_matches_filters(item, filters)]
    listings = sort_listings(listings, sort_by)
    if per_page > 0:
        listings = listings[:per_page]

    pages = (total + LUBEAVTO_PAGE_SIZE - 1) // LUBEAVTO_PAGE_SIZE if total else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        market_total=total,
    )


async def search_lubeavto(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_lubeavto_body(filters, page=page, per_page=per_page, sort_by=sort_by)

    return await get_or_fetch(
        _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by),
        lambda: _search_lubeavto_body(filters, page=page, per_page=per_page, sort_by=sort_by),
        ttl_seconds=cache_ttl_seconds,
    )


async def fetch_lubeavto_pool(
    filters: SearchFilters,
    *,
    need: int,
    sort_by: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    need = max(need, 1)
    collected: list[ListingOut] = []
    seen: set[str] = set()
    total = 0
    page = 1
    max_pages = min(
        LUBEAVTO_MAX_PAGES,
        max((need + LUBEAVTO_PAGE_SIZE - 1) // LUBEAVTO_PAGE_SIZE, 1),
    )

    while len(collected) < need and page <= max_pages:
        chunk = await search_lubeavto(
            filters,
            page=page,
            per_page=LUBEAVTO_PAGE_SIZE,
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        total = max(total, chunk.total)
        for item in chunk.items:
            if item.id in seen:
                continue
            seen.add(item.id)
            collected.append(item)
            if len(collected) >= need:
                break
        if len(chunk.items) < LUBEAVTO_PAGE_SIZE:
            break
        page += 1

    collected = sort_listings(collected[:need], sort_by)
    pages = (total + need - 1) // need if total else 0
    return PaginatedListings(
        items=collected,
        total=max(total, len(collected)),
        page=1,
        per_page=need,
        pages=pages,
        market_total=total,
    )
