from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria_beta.client import AutoRiaBetaClient
from app.services.auto_ria_beta.constants import (
    INITIAL_HTML_PAGES,
    MAX_PAGES,
    PAGE_SIZE,
    POOL_MAX_ITEMS,
)
from app.services.auto_ria_beta.errors import AutoRiaBetaError
from app.services.auto_ria_beta.mapper import (
    apply_client_filters,
    filters_to_html_params,
    listings_from_cars,
)

logger = logging.getLogger(__name__)


@dataclass
class AutoRiaBetaBatch:
    listings: list
    market_total: int
    next_html_page: int
    exhausted: bool

    def to_page(self, *, need: int) -> PaginatedListings:
        items = list(self.listings)
        total = max(self.market_total, len(items))
        return PaginatedListings(
            items=items,
            total=total,
            page=1,
            per_page=need,
            pages=(total + PAGE_SIZE - 1) // PAGE_SIZE if total else 0,
            market_total=self.market_total,
        )


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "auto_ria_beta",
        "beta_v": "html-v3",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def fetch_auto_ria_beta_batch(
    filters: SearchFilters,
    *,
    sort_by: str,
    start_page: int = 0,
    html_pages: int = INITIAL_HTML_PAGES,
    need: int | None = None,
    seen_ids: set[int] | None = None,
) -> AutoRiaBetaBatch:
    """Тягне обмежену кількість HTML-сторінок пошуку (без повного обходу каталогу)."""
    cap = min(need, POOL_MAX_ITEMS) if need is not None else POOL_MAX_ITEMS
    html_pages = max(html_pages, 1)
    start_page = max(start_page, 0)
    client = AutoRiaBetaClient()
    collected_cars = []
    seen: set[int] = set(seen_ids or ())
    total = 0
    html_page = start_page
    last_page = min(start_page + html_pages, MAX_PAGES)
    exhausted = start_page >= MAX_PAGES

    while html_page < last_page and len(collected_cars) < cap:
        params = await filters_to_html_params(filters, page=html_page, size=PAGE_SIZE)
        try:
            page_cars, page_total = await client.fetch_search_page(params)
        except AutoRiaBetaError:
            logger.warning("auto_ria_beta html page=%s failed", html_page, exc_info=True)
            exhausted = True
            break

        total = max(total, page_total)
        added = 0
        for car in apply_client_filters(page_cars, filters):
            if car.car_id in seen:
                continue
            seen.add(car.car_id)
            collected_cars.append(car)
            added += 1
            if len(collected_cars) >= cap:
                break

        html_page += 1
        if not page_cars:
            exhausted = True
            break
        if total and (len(seen) >= total or (start_page == 0 and len(collected_cars) >= total)):
            exhausted = True
            break
        if added == 0 and not page_cars:
            exhausted = True
            break

    if html_page >= MAX_PAGES:
        exhausted = True
    if total and len(seen) >= total:
        exhausted = True

    listings = listings_from_cars(collected_cars[:cap], filters, sort_by=sort_by)
    return AutoRiaBetaBatch(
        listings=listings,
        market_total=total,
        next_html_page=html_page,
        exhausted=exhausted,
    )


async def _search_auto_ria_beta_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    enrich_details: bool = False,
) -> PaginatedListings:
    del enrich_details
    html_page = max(page - 1, 0)
    batch = await fetch_auto_ria_beta_batch(
        filters,
        sort_by=sort_by,
        start_page=html_page,
        html_pages=1,
        need=max(per_page, 1),
    )
    listings = list(batch.listings)
    if per_page > 0:
        listings = listings[:per_page]
    total = max(batch.market_total, len(listings))
    pages = (total + per_page - 1) // per_page if total and per_page else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        market_total=batch.market_total,
    )


async def search_auto_ria_beta(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    enrich_details: bool = False,
) -> PaginatedListings:
    if not use_cache:
        return await _search_auto_ria_beta_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            enrich_details=enrich_details,
        )

    return await get_or_fetch(
        _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by),
        lambda: _search_auto_ria_beta_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            enrich_details=enrich_details,
        ),
        ttl_seconds=cache_ttl_seconds,
    )


async def fetch_auto_ria_beta_pool(
    filters: SearchFilters,
    *,
    need: int,
    sort_by: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    start_page: int = 0,
    html_pages: int = INITIAL_HTML_PAGES,
) -> PaginatedListings:
    del use_cache, cache_ttl_seconds
    need = min(max(need, 1), POOL_MAX_ITEMS)
    batch = await fetch_auto_ria_beta_batch(
        filters,
        sort_by=sort_by,
        start_page=start_page,
        html_pages=html_pages,
        need=need,
    )
    page = batch.to_page(need=need)
    object.__setattr__(
        page,
        "_beta_cursor",
        {"next_html_page": batch.next_html_page, "exhausted": batch.exhausted},
    )
    return page
