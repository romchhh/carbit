from __future__ import annotations

import asyncio

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
from app.services.auto_ria.mapper import filters_to_search_params, info_to_listing, sort_listings


async def search_auto_ria(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "price_asc",
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
    auto_ids = [str(item) for item in raw_ids if item]

    sem = asyncio.Semaphore(5)

    async def fetch_one(auto_id: str) -> ListingOut | None:
        async with sem:
            try:
                info = await client.get_info(auto_id)
                return info_to_listing(info)
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
