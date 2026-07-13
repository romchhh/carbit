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
    OlxSearchParams,
    apply_details_to_listing,
    build_search_url,
    has_next_page,
    html_looks_like_results_page,
    listing_needs_enrichment,
    parse_listing_page,
    passes_olx_filters,
)
from app.services.olx.errors import OlxError
from app.services.search.concurrency import acquire_olx_slot
from app.services.telegram.admin_alerts import notify_admin_parsing_error


def _switch_params_to_text_query(params: OlxSearchParams, filters: SearchFilters) -> OlxSearchParams:
    """Fallback, коли /brand/model/ на OLX дає 404 → /q-{brand}/ + пост-фільтр."""
    brand = (filters.brand or "").strip()
    if not brand:
        return params
    params.text_query = brand
    params.brand_label = brand
    if filters.model:
        params.model_label = filters.model.strip()
    params.brand = None
    params.model = None
    return params


async def _fetch_olx_search_html(
    client: OlxClient,
    params: OlxSearchParams,
    filters: SearchFilters,
    *,
    page: int,
) -> tuple[str, OlxSearchParams, str]:
    url = build_search_url(params, page=page)
    try:
        html = await client.fetch_html(url)
        return html, params, url
    except OlxError as exc:
        if (
            exc.status_code == 404
            and not params.text_query
            and (filters.brand or filters.model)
        ):
            params = _switch_params_to_text_query(params, filters)
            url = build_search_url(params, page=page)
            html = await client.fetch_html(url)
            return html, params, url
        raise


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
    sort_by: str = "newest",
) -> PaginatedListings:
    async with acquire_olx_slot():
        return await _search_olx_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )


async def _search_olx_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    # Менше overscan: live path передає вже обмежений per_page (SOURCE_POOL_CAP)
    max_pages = min(max(page, 1) + 1, 3)
    params = filters_to_olx_params(filters, max_pages=max_pages)
    if params.needs_post_filter():
        params.max_pages = min(max(params.max_pages, 2), 4)

    collected: list[OlxListing] = []
    pages_scanned = 0
    start_page = max(page - 1, 0) * 2 + 1
    # Було ×2/×3 — часто впиралось у 15s timeout на великих пулах
    target_count = per_page + max(per_page // 2, 8) if params.needs_post_filter() else per_page
    enrich_sem = asyncio.Semaphore(3)

    async with OlxClient() as client:

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
            html, params, url = await _fetch_olx_search_html(
                client, params, filters, page=current_page
            )
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

            candidates: list[OlxListing] = [
                listing for listing in page_listings if passes_olx_filters(listing, params)
            ]
            to_enrich = [
                listing for listing in candidates if listing_needs_enrichment(listing, params)
            ]
            if to_enrich:
                await asyncio.gather(*(enrich_listing(listing) for listing in to_enrich))

            for listing in candidates:
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
    sort_by: str = "newest",
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
