from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, SearchQuery, Source, User
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.mapper import sort_listings
from app.services.listings.serialize import listing_to_out
from app.services.listings.upsert import upsert_listing
from app.services.parser.filter_groups import parse_search_filters
from app.services.parser.linking import link_listing_to_search
from app.services.parser.settings import get_parser_settings
from app.services.telegram_channels.mapper import car_listing_to_listing_out, listing_out_matches_filters


async def ingest_telegram_listing(
    db: AsyncSession,
    car_listing,
    *,
    notify: bool = True,
    link_searches: bool = True,
) -> tuple[ListingOut, int, int]:
    """Upsert telegram listing and optionally link to matching active searches."""
    item = car_listing_to_listing_out(car_listing)
    listing = await upsert_listing(db, item)

    if not link_searches:
        return item, 0, 0

    parser_settings = await get_parser_settings()
    if not parser_settings.get("notify_telegram", True):
        notify = False

    searches = await db.scalars(select(SearchQuery).where(SearchQuery.is_active.is_(True)))
    new_total = 0
    notifications = 0
    users_cache: dict[str, User | None] = {}

    for search in searches.all():
        filters = parse_search_filters(search.filters)
        sources = filters.sources
        if sources and "telegram" not in [s.lower() for s in sources]:
            continue
        if not listing_out_matches_filters(item, filters):
            continue

        if search.user_id not in users_cache:
            users_cache[search.user_id] = await db.get(User, search.user_id)
        user = users_cache[search.user_id]
        is_new, sent = await link_listing_to_search(
            db,
            search=search,
            listing_id=listing.id,
            notify=notify,
            user=user,
        )
        if is_new:
            new_total += 1
        if sent:
            notifications += 1

    return item, new_total, notifications


async def search_telegram_listings(
    db: AsyncSession,
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "price_asc",
    max_scan: int = 500,
) -> PaginatedListings:
    rows = await db.scalars(
        select(Listing)
        .where(Listing.source == Source.telegram)
        .order_by(Listing.published_at.desc())
        .limit(max_scan)
    )
    matched: list[ListingOut] = []
    for listing in rows.all():
        item = listing_to_out(listing)
        if listing_out_matches_filters(item, filters):
            matched.append(item)

    matched = sort_listings(matched, sort_by)
    total = len(matched)
    start = (page - 1) * per_page
    page_items = matched[start : start + per_page]
    pages = (total + per_page - 1) // per_page if total else 0

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
