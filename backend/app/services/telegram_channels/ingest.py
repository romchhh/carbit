from __future__ import annotations

import logging

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, SearchQuery, Source, User
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.mapper import sort_listings
from app.services.listings.serialize import listing_to_out
from app.services.listings.upsert import upsert_listing
from app.services.parser.filter_groups import parse_search_filters
from app.services.parser.linking import link_listing_to_search
from app.services.parser.settings import get_parser_settings
from app.services.telegram_channels.mapper import (
    car_listing_to_listing_out,
    listing_out_matches_filters,
    telegram_listing_id,
)

logger = logging.getLogger(__name__)


def _save_photo_refs_from_car(car_listing) -> str:
    """Зберігає refs для lazy download; повертає listing_id."""
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    listing_id = telegram_listing_id(car_listing.channel, car_listing.message_id)
    ids = list(car_listing.group_message_ids or []) or [car_listing.message_id]
    ChannelMediaStore().save_photo_refs(listing_id, car_listing.channel, ids)
    return listing_id


async def ingest_telegram_listing(
    db: AsyncSession,
    car_listing,
    *,
    notify: bool = True,
    link_searches: bool = True,
) -> tuple[ListingOut, int, int, bool]:
    """Upsert telegram listing and optionally link to matching active searches.

    Returns (item, new_links, notifications, matched_any_search).
    Фото не качає — лише зберігає refs; download робить worker при match / queue.
    """
    item = car_listing_to_listing_out(car_listing)
    _save_photo_refs_from_car(car_listing)
    listing = await upsert_listing(db, item)

    if not link_searches:
        return item, 0, 0, False

    parser_settings = await get_parser_settings()
    if not parser_settings.get("notify_telegram", True):
        notify = False

    searches = await db.scalars(select(SearchQuery).where(SearchQuery.is_active.is_(True)))
    new_total = 0
    notifications = 0
    matched_any = False
    users_cache: dict[str, User | None] = {}

    for search in searches.all():
        filters = parse_search_filters(search.filters)
        sources = filters.sources
        if sources and "telegram" not in [s.lower() for s in sources]:
            continue
        if not listing_out_matches_filters(item, filters):
            continue

        matched_any = True
        if search.user_id not in users_cache:
            users_cache[search.user_id] = await db.get(User, search.user_id)
        user = users_cache[search.user_id]
        is_new, sent = await link_listing_to_search(
            db,
            search=search,
            listing_id=listing.id,
            notify=notify,
            user=user,
            max_notification_hours=parser_settings.get("notification_max_published_hours", 1),
        )
        if is_new:
            new_total += 1
        if sent:
            notifications += 1

    if matched_any:
        from app.services.telegram_channels.bootstrap import ensure_parser_path

        ensure_parser_path()
        from parser.channel_media_store import ChannelMediaStore

        ChannelMediaStore().enqueue_photo_download(item.id)

    return item, new_total, notifications, matched_any


def _telegram_sql_prefilters(filters: SearchFilters):
    """Грубі SQL-предикати — менше рядків тягнемо в Python."""
    clauses = [Listing.source == Source.telegram]

    brand = (filters.brand or "").strip()
    if brand:
        like = f"%{brand}%"
        clauses.append(
            or_(
                Listing.brand.ilike(like),
                Listing.title.ilike(like),
                Listing.description.ilike(like),
            )
        )

    model = (filters.model or "").strip()
    if model:
        like = f"%{model}%"
        clauses.append(
            or_(
                Listing.model.ilike(like),
                Listing.title.ilike(like),
                Listing.description.ilike(like),
            )
        )

    if filters.year_from or filters.year_to:
        clauses.append(Listing.year > 0)
        if filters.year_from:
            clauses.append(Listing.year >= filters.year_from)
        if filters.year_to:
            clauses.append(Listing.year <= filters.year_to)

    if filters.mileage_from:
        clauses.append(
            or_(Listing.mileage == 0, Listing.mileage >= filters.mileage_from)
        )
    if filters.mileage_to:
        clauses.append(
            or_(Listing.mileage == 0, Listing.mileage <= filters.mileage_to)
        )

    return and_(*clauses)


async def search_telegram_listings(
    db: AsyncSession,
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    max_scan: int = 3000,
    keyword_refresh: bool = True,
) -> PaginatedListings:
    if keyword_refresh:
        try:
            from app.services.telegram_channels.keyword_refresh import (
                refresh_telegram_by_keywords,
            )

            await refresh_telegram_by_keywords(filters)
        except Exception:
            logger.exception("Telegram keyword refresh failed")

    rows = await db.scalars(
        select(Listing)
        .where(_telegram_sql_prefilters(filters))
        .order_by(Listing.published_at.desc())
        .limit(max_scan)
    )
    matched: list[ListingOut] = []
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.channel_media_store import ChannelMediaStore

    media_store = ChannelMediaStore()
    for listing in rows.all():
        item = listing_to_out(listing)
        if listing_out_matches_filters(item, filters):
            matched.append(item)
            # Підвантажити фото для знайдених у пошуку без картинок
            if not (item.images or []):
                media_store.enqueue_photo_download(item.id)

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
