from __future__ import annotations

import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.car_market.client import CarMarketClient
from app.services.car_market.constants import CAR_MARKET_MAX_PAGES, CAR_MARKET_PAGE_SIZE
from app.services.car_market.errors import CarMarketBrandNotFound, CarMarketError
from app.services.car_market.mapper import car_to_listing, filters_to_search_params
from app.services.search.filter_multi import effective_brands
from app.services.telegram_channels.mapper import listing_out_matches_filters


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "car_market",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_car_market_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = CarMarketClient()
    brand_hint = (effective_brands(filters) or [None])[0]

    try:
        params = filters_to_search_params(filters, page=page)
    except CarMarketBrandNotFound:
        return PaginatedListings(
            items=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=0,
            market_total=0,
        )

    brand_param_used = "brands" in params

    try:
        cars, total = await client.fetch_catalog(params)
        if brand_param_used and not cars:
            # Деякі brand ID не рендеряться в SSR — тягнемо каталог і фільтруємо в Python.
            fallback_params = {key: value for key, value in params.items() if key != "brands"}
            cars, total = await client.fetch_catalog(fallback_params)
    except ValueError as exc:
        raise CarMarketError(str(exc)) from exc

    listings: list[ListingOut] = []
    for car in cars:
        if car.is_sold:
            continue
        listing = car_to_listing(car, brand_hint=brand_hint)
        if listing_out_matches_filters(listing, filters):
            listings.append(listing)

    listings = sort_listings(listings, sort_by)
    if per_page > 0:
        listings = listings[:per_page]

    pages = (total + CAR_MARKET_PAGE_SIZE - 1) // CAR_MARKET_PAGE_SIZE if total else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        market_total=total,
    )


async def search_car_market(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_car_market_body(filters, page=page, per_page=per_page, sort_by=sort_by)

    return await get_or_fetch(
        _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by),
        lambda: _search_car_market_body(filters, page=page, per_page=per_page, sort_by=sort_by),
        ttl_seconds=cache_ttl_seconds,
    )


async def fetch_car_market_pool(
    filters: SearchFilters,
    *,
    need: int,
    sort_by: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    """Збирає пул з кількох сторінок (обмежено CAR_MARKET_MAX_PAGES)."""
    need = max(need, 1)
    collected: list[ListingOut] = []
    seen: set[str] = set()
    total = 0
    page = 1
    max_pages = min(
        CAR_MARKET_MAX_PAGES,
        max((need + CAR_MARKET_PAGE_SIZE - 1) // CAR_MARKET_PAGE_SIZE, 1),
    )
    skip_brand_param = False

    while len(collected) < need and page <= max_pages:
        chunk_filters = filters
        if skip_brand_param and (filters.brand or filters.brands):
            payload = filters.model_dump()
            payload["brand"] = None
            payload["brands"] = None
            chunk_filters = SearchFilters.model_validate(payload)

        chunk = await search_car_market(
            chunk_filters,
            page=page,
            per_page=CAR_MARKET_PAGE_SIZE,
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        if page == 1 and not chunk.items and (filters.brand or filters.brands) and not skip_brand_param:
            skip_brand_param = True
            continue

        total = max(total, chunk.total)
        for item in chunk.items:
            if item.id in seen:
                continue
            seen.add(item.id)
            collected.append(item)
            if len(collected) >= need:
                break
        if len(chunk.items) < CAR_MARKET_PAGE_SIZE:
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
