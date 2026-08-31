from __future__ import annotations

import asyncio
import json
import logging

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.reono.client import ReonoClient
from app.services.reono.constants import HEADERS, REONO_MAX_PAGES, REONO_PAGE_SIZE
from app.services.reono.errors import ReonoError
from app.services.reono.mapper import apply_client_filters, car_to_listing
from app.services.reono.images import valid_reono_cdn_urls
from app.services.telegram_channels.mapper import listing_out_matches_filters

logger = logging.getLogger(__name__)


async def _enrich_accident_descriptions(listings: list[ListingOut], filters: SearchFilters) -> list[ListingOut]:
    if not filters.accident or not listings:
        return listings

    from app.services.listings.scraped_description import apply_descriptions, fetch_descriptions_by_url
    from app.services.reono.detail import parse_detail_description

    async def _fetch_html(client, url: str) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    descriptions = await fetch_descriptions_by_url(
        [item.url for item in listings],
        fetch_html=_fetch_html,
        parse_description=parse_detail_description,
        headers=HEADERS,
    )
    return apply_descriptions(listings, descriptions, source_key="reono")


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "reono",
        "reono_v": "car-card-v3",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _needs_published_date_enrich(filters: SearchFilters) -> bool:
    return bool(
        filters.published_older_than_days
        or filters.published_within_days
        or filters.published_within_hours
        or filters.published_from
        or filters.published_to
    )


async def _enrich_listing_details(
    listings: list[ListingOut],
    *,
    fetch_dates: bool,
) -> list[ListingOut]:
    """Підтягує фото та/або дату публікації зі сторінки оголошення (один HTTP-запит)."""
    from app.services.reono.lazy_photos import fetch_reono_listing_detail

    from app.services.listings.plate import resolve_listing_plate

    async def enrich_one(item: ListingOut) -> ListingOut:
        needs_images = len(valid_reono_cdn_urls(item.images or [])) < 2
        needs_dates = fetch_dates
        needs_plate = resolve_listing_plate(item) is None
        if not item.url or (not needs_images and not needs_dates and not needs_plate):
            return item
        try:
            detail = await fetch_reono_listing_detail(item.url)
        except Exception:
            logger.debug("REONO detail enrich failed for %s", item.id, exc_info=True)
            return item

        update: dict = {}
        source_data = dict(item.source_data or {})
        nested = dict(source_data.get("reono") or {})
        source_data_changed = False

        if needs_images and detail.images:
            update["images"] = detail.images
        if detail.published_at is not None:
            update["published_at"] = detail.published_at
            update["found_at"] = detail.published_at
            nested["published_at"] = detail.published_at.isoformat()
            source_data_changed = True
        if detail.plate:
            update["plate"] = detail.plate
            nested["plateNumber"] = detail.plate
            source_data_changed = True
        if source_data_changed:
            source_data["reono"] = nested
            update["source_data"] = source_data
        if not update:
            return item
        return item.model_copy(update=update)

    sem = asyncio.Semaphore(5)

    async def limited(item: ListingOut) -> ListingOut:
        async with sem:
            return await enrich_one(item)

    return list(await asyncio.gather(*(limited(item) for item in listings)))


async def _search_reono_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = ReonoClient()
    try:
        cars, total = await client.fetch_catalog(filters, page=page)
    except ValueError as exc:
        raise ReonoError(str(exc)) from exc

    cars = apply_client_filters(cars, filters)
    listings: list[ListingOut] = []
    for car in cars:
        listing = car_to_listing(car)
        listings.append(listing)

    listings = await _enrich_accident_descriptions(listings, filters)
    listings = await _enrich_listing_details(
        listings,
        fetch_dates=_needs_published_date_enrich(filters),
    )
    listings = [item for item in listings if listing_out_matches_filters(item, filters)]

    listings = sort_listings(listings, sort_by)
    if per_page > 0:
        listings = listings[:per_page]

    pages = (total + REONO_PAGE_SIZE - 1) // REONO_PAGE_SIZE if total else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        market_total=total,
    )


async def search_reono(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_reono_body(filters, page=page, per_page=per_page, sort_by=sort_by)

    return await get_or_fetch(
        _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by),
        lambda: _search_reono_body(filters, page=page, per_page=per_page, sort_by=sort_by),
        ttl_seconds=cache_ttl_seconds,
    )


async def fetch_reono_pool(
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
        REONO_MAX_PAGES,
        max((need + REONO_PAGE_SIZE - 1) // REONO_PAGE_SIZE, 1),
    )

    while len(collected) < need and page <= max_pages:
        chunk = await search_reono(
            filters,
            page=page,
            per_page=REONO_PAGE_SIZE,
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
        if len(chunk.items) < REONO_PAGE_SIZE:
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
