from __future__ import annotations

import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.telegram_channels.mapper import listing_out_matches_filters
from app.services.udrive.catalog import get_makes_by_id
from app.services.udrive.client import UdriveClient
from app.services.udrive.errors import UdriveBrandNotFound, UdriveError
from app.services.udrive.mapper import car_to_listing, filters_to_query_body


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "udrive",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_udrive_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = UdriveClient()
    try:
        body, brand_slug = await filters_to_query_body(
            client,
            filters,
            page=page,
            per_page=per_page,
        )
        data = await client.query_cars(body)
    except UdriveBrandNotFound:
        return PaginatedListings(
            items=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=0,
            market_total=0,
        )
    except ValueError as exc:
        raise UdriveError(str(exc)) from exc

    rows = data.get("items") or []
    total = int(data.get("total") or len(rows))
    last_page = int(data.get("last") or 0)
    currency = (filters.currency or "USD").upper()
    makes_by_id = await get_makes_by_id(client)

    # Жорстка перевірка make/model як у udrivetest.py
    make_ids = set(body.get("makeId") or [])
    model_ids = set(body.get("modelId") or [])

    listings: list[ListingOut] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = row.get("model") if isinstance(row.get("model"), dict) else {}
        if make_ids and model.get("makeId") not in make_ids:
            continue
        if model_ids and model.get("id") not in model_ids:
            continue
        listing = car_to_listing(
            row,
            brand_slug=brand_slug,
            makes_by_id=makes_by_id,
            currency=currency,
        )
        if listing_out_matches_filters(listing, filters):
            listings.append(listing)

    listings = sort_listings(listings, sort_by)
    pages = last_page
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


async def search_udrive(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_udrive_body(filters, page=page, per_page=per_page, sort_by=sort_by)

    return await get_or_fetch(
        _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by),
        lambda: _search_udrive_body(filters, page=page, per_page=per_page, sort_by=sort_by),
        ttl_seconds=cache_ttl_seconds,
    )
