from __future__ import annotations

import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.lubeavto.client import LubeAvtoClient
from app.services.lubeavto.constants import (
    LUBEAVTO_MAX_PAGES,
    LUBEAVTO_PAGE_SIZE,
    STOCK_CATALOGS,
)
from app.services.lubeavto.errors import LubeAvtoError
from app.services.lubeavto.mapper import car_to_listing, filters_to_catalog_path
from app.services.search.filter_multi import effective_brands
from app.services.telegram_channels.mapper import listing_out_matches_filters


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "lubeavto",
        "lubeavto_v": "stock-v2",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _catalog_paths(filters: SearchFilters, catalog: str) -> list[str]:
    """Бренд/модель, потім лише бренд. Без кореневого каталогу — він дає 1500 чужих авто."""
    paths: list[str] = []
    primary = filters_to_catalog_path(filters, catalog=catalog)
    paths.append(primary)
    if effective_brands(filters) and (filters.model or filters.models):
        brand_only = filters_to_catalog_path(
            filters.model_copy(update={"model": None, "models": None}),
            catalog=catalog,
        )
        if brand_only not in paths:
            paths.append(brand_only)
    return paths


async def _fetch_catalog_cars(
    client: LubeAvtoClient,
    filters: SearchFilters,
    *,
    catalog: str,
    page_number: int,
) -> tuple[list, int]:
    last_total = 0
    for path in _catalog_paths(filters, catalog):
        cars, total = await client.fetch_catalog(
            path,
            page_number=page_number,
            catalog=catalog,
        )
        last_total = total
        if cars:
            return cars, total
    return [], last_total if not effective_brands(filters) else 0


async def _search_lubeavto_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = LubeAvtoClient()
    brand_hint = (effective_brands(filters) or [None])[0]
    page_number = max(page - 1, 0)

    cars: list = []
    seen: set[str] = set()
    site_total = 0
    try:
        for catalog in STOCK_CATALOGS:
            chunk, total = await _fetch_catalog_cars(
                client,
                filters,
                catalog=catalog,
                page_number=page_number,
            )
            site_total += total
            for car in chunk:
                key = f"{car.catalog}:{car.car_id}"
                if key in seen:
                    continue
                seen.add(key)
                cars.append(car)
    except ValueError as exc:
        raise LubeAvtoError(str(exc)) from exc

    listings: list[ListingOut] = []
    for car in cars:
        listings.append(car_to_listing(car, brand_hint=brand_hint))

    listings = [item for item in listings if listing_out_matches_filters(item, filters)]
    listings = sort_listings(listings, sort_by)
    matched = len(listings)
    if per_page > 0:
        listings = listings[:per_page]

    total = matched if effective_brands(filters) else max(site_total, matched)
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
            per_page=max(need, LUBEAVTO_PAGE_SIZE),
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        total = max(total, chunk.total, chunk.market_total or 0)
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
    matched = len(collected)
    total = matched if effective_brands(filters) else max(total, matched)
    pages = (total + need - 1) // need if total else 0
    return PaginatedListings(
        items=collected,
        total=total,
        page=1,
        per_page=need,
        pages=pages,
        market_total=total,
    )
