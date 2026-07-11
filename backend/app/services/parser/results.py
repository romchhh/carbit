from __future__ import annotations

from datetime import datetime

from app.core.timezone import as_kyiv, now_kyiv

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, SearchListing, SearchQuery
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.listings.serialize import listing_to_out
from app.services.parser.filter_groups import filters_group_key


def _sort_items(items: list[tuple[ListingOut, datetime]], sort_by: str) -> list[ListingOut]:
    if sort_by == "price_asc":
        return [item for item, _ in sorted(items, key=lambda row: row[0].price)]
    if sort_by == "price_desc":
        return [item for item, _ in sorted(items, key=lambda row: row[0].price, reverse=True)]
    if sort_by == "year_desc":
        return [item for item, _ in sorted(items, key=lambda row: row[0].year, reverse=True)]
    if sort_by == "mileage_asc":
        return [item for item, _ in sorted(items, key=lambda row: row[0].mileage)]
    if sort_by in ("newest", "published_desc"):
        return [
            item
            for item, _ in sorted(items, key=lambda row: as_kyiv(row[0].published_at), reverse=True)
        ]
    return [item for item, _ in sorted(items, key=lambda row: row[1], reverse=True)]


async def get_search_results_from_db(
    db: AsyncSession,
    search: SearchQuery,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    new_only: bool = False,
) -> PaginatedListings:
    stmt = (
        select(Listing, SearchListing)
        .join(SearchListing, SearchListing.listing_id == Listing.id)
        .where(SearchListing.search_id == search.id)
    )
    if new_only:
        stmt = stmt.where(SearchListing.is_new.is_(True))

    rows = (await db.execute(stmt)).all()
    paired = [(listing_to_out(listing), as_kyiv(listing.published_at)) for listing, sl in rows]
    items = _sort_items(paired, sort_by)

    total = len(items)
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]
    pages = (total + per_page - 1) // per_page if total else 0

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def get_cached_preview_results(
    db: AsyncSession,
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings | None:
    from app.services.parser.settings import get_filter_cache, get_parser_settings

    settings = await get_parser_settings()
    cache = await get_filter_cache(filters_group_key(filters))
    if not cache:
        return None

    fetched_at = cache.get("fetched_at")
    if not fetched_at:
        return None

    try:
        fetched = as_kyiv(datetime.fromisoformat(fetched_at))
    except ValueError:
        return None

    age = (now_kyiv() - fetched).total_seconds()
    if age > settings["cache_ttl_seconds"]:
        return None

    listing_ids = cache.get("listing_ids") or []
    if not listing_ids:
        return PaginatedListings(items=[], total=0, page=page, per_page=per_page, pages=0)

    result = await db.scalars(select(Listing).where(Listing.id.in_(listing_ids)))
    listings = {item.id: item for item in result.all()}
    paired = [
        (listing_to_out(listings[lid]), as_kyiv(listings[lid].published_at))
        for lid in listing_ids
        if lid in listings
    ]
    try:
        items = _sort_items(paired, sort_by)
    except Exception:
        items = [item for item, _ in paired]

    # Старий кеш без total ламав «Показати ще» (total == len(ids) ≈ 20).
    # Без збереженого total не використовуємо кеш — йдемо в живий пошук.
    cached_total = cache.get("total")
    if cached_total is None:
        return None

    try:
        total = int(cached_total)
    except (TypeError, ValueError):
        return None
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]
    pages = int(cache["pages"]) if cache.get("pages") is not None else (
        (total + per_page - 1) // per_page if total else 0
    )

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def mark_search_listings_seen(db: AsyncSession, search: SearchQuery) -> int:
    rows = await db.scalars(
        select(SearchListing).where(
            SearchListing.search_id == search.id,
            SearchListing.is_new.is_(True),
        )
    )
    count = 0
    for row in rows.all():
        row.is_new = False
        count += 1
    search.new_count = 0
    await db.flush()
    return count
