from __future__ import annotations

import asyncio
import json
import random

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.olx.client import OlxClient
from app.services.olx.constants import MAX_DELAY, MIN_DELAY
from app.services.olx.mapper import filters_to_olx_params, olx_listing_to_listing_out
from app.services.olx.parser import (
    OlxListing,
    apply_details_to_listing,
    build_search_url,
    has_next_page,
    html_looks_like_results_page,
    listing_needs_enrichment,
    parse_listing_page,
    passes_olx_filters,
)
from app.services.olx.errors import OlxError
from app.services.telegram.admin_alerts import notify_admin_parsing_error


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "olx",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_olx_uncached(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "price_asc",
) -> PaginatedListings:
    client = OlxClient()
    params = filters_to_olx_params(filters, max_pages=min(page + 2, 6))
    if params.needs_post_filter():
        params.max_pages = max(params.max_pages, 4)

    collected: list[OlxListing] = []
    pages_scanned = 0
    start_page = max(page - 1, 0) * 2 + 1
    target_count = per_page * 3 if params.needs_post_filter() else per_page * 2
    enrich_sem = asyncio.Semaphore(3)

    async def enrich_listing(listing: OlxListing) -> OlxListing:
        if not listing.url:
            return listing
        async with enrich_sem:
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            details = await client.fetch_listing_details(listing.url)
        apply_details_to_listing(listing, details)
        return listing

    while pages_scanned < params.max_pages and len(collected) < target_count:
        current_page = start_page + pages_scanned
        url = build_search_url(params, page=current_page)
        html = await client.fetch_html(url)
        try:
            page_listings = await asyncio.to_thread(parse_listing_page, html)
        except Exception as exc:
            message = f"Виняток при парсингу сторінки видачі OLX: {exc}"
            await notify_admin_parsing_error(
                source="OLX",
                error=message,
                url=url,
                details=type(exc).__name__,
            )
            raise OlxError("Помилка парсингу OLX") from exc

        if not page_listings and pages_scanned == 0 and html_looks_like_results_page(html):
            await notify_admin_parsing_error(
                source="OLX",
                error="Сторінка видачі OLX завантажена, але оголошення не розпарсились",
                url=url,
                details="Ймовірно змінився HTML OLX — перевірте селектори парсера",
            )
        if not page_listings:
            break

        for listing in page_listings:
            if not passes_olx_filters(listing, params):
                continue
            if listing_needs_enrichment(listing, params):
                listing = await enrich_listing(listing)
            if not passes_olx_filters(listing, params):
                continue
            collected.append(listing)
            if len(collected) >= target_count:
                break

        pages_scanned += 1
        if not has_next_page(html, current_page):
            break
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    items = [
        olx_listing_to_listing_out(
            listing,
            brand_hint=filters.brand or "",
            model_hint=filters.model or "",
        )
        for listing in collected
    ]
    items = sort_listings(items, sort_by)

    start = 0
    end = per_page
    page_items = items[start:end]
    total = max(len(items), len(page_items))
    pages = max((total + per_page - 1) // per_page, 1 if page_items else 0)

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def search_olx(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "price_asc",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_olx_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )

    key = _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by)
    return await get_or_fetch(
        key,
        lambda: _search_olx_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        ),
        ttl_seconds=cache_ttl_seconds,
    )
