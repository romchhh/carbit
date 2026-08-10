from __future__ import annotations

import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.imperiya.client import ImperiyaClient, ImperiyaError
from app.services.imperiya.mapper import ad_to_listing, filters_to_search_params
from app.services.telegram_channels.mapper import listing_out_matches_filters


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "imperiya",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_imperiya_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = ImperiyaClient()
    try:
        params = await filters_to_search_params(
            client,
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )
        data = await client.search_cars(params)
    except ValueError as exc:
        raise ImperiyaError(str(exc)) from exc

    rows = data.get("data") or []
    pagination = data.get("pagination") or {}
    total = int(pagination.get("totalOffersCount") or len(rows))
    currency = (filters.currency or "USD").upper()

    listings: list[ListingOut] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        listing = ad_to_listing(row, currency=currency)
        if listing_out_matches_filters(listing, filters):
            listings.append(listing)

    listings = sort_listings(listings, sort_by)
    pages = int(pagination.get("totalPageCount") or 0)
    if not pages and total:
        pages = (total + per_page - 1) // per_page

    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        market_total=total,
    )


async def search_imperiya(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_imperiya_body(filters, page=page, per_page=per_page, sort_by=sort_by)

    return await get_or_fetch(
        _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by),
        lambda: _search_imperiya_body(filters, page=page, per_page=per_page, sort_by=sort_by),
        ttl_seconds=cache_ttl_seconds,
    )
