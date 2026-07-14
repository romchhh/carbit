from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import Listing, SearchListing, SearchQuery, User
from app.services.notifications.freshness import (
    coerce_notification_max_hours,
    is_listing_fresh_for_notification,
)
from app.services.notifications.service import create_listing_notification
from app.services.parser.settings import get_parser_settings


async def link_listing_to_search(
    db: AsyncSession,
    *,
    search: SearchQuery,
    listing_id: str,
    notify: bool,
    user: User | None,
    max_notification_hours: float | None = None,
    mark_as_new: bool = True,
) -> tuple[bool, bool]:
    """Returns (is_new_link, notification_sent).

    mark_as_new=False — baseline при збереженні моніторингу (авто з першого пошуку).
    """
    existing = await db.scalar(
        select(SearchListing).where(
            SearchListing.search_id == search.id,
            SearchListing.listing_id == listing_id,
        )
    )
    if existing:
        return False, False

    db.add(
        SearchListing(
            search_id=search.id,
            listing_id=listing_id,
            is_new=mark_as_new,
            first_seen_at=now_kyiv(),
        )
    )
    if mark_as_new:
        search.new_count = (search.new_count or 0) + 1
    search.total_count = (search.total_count or 0) + 1
    search.last_checked_at = now_kyiv()

    notification_sent = False
    if mark_as_new and notify and user and user.telegram_connected:
        listing = await db.get(Listing, listing_id)
        if listing:
            if max_notification_hours is None:
                settings = await get_parser_settings()
                max_notification_hours = coerce_notification_max_hours(
                    settings.get("notification_max_published_hours", 1)
                )
            else:
                max_notification_hours = coerce_notification_max_hours(max_notification_hours)
            if is_listing_fresh_for_notification(
                listing.published_at,
                max_hours=max_notification_hours,
            ):
                notification = await create_listing_notification(
                    db,
                    user,
                    listing,
                    search=search,
                    max_published_hours=max_notification_hours,
                )
                notification_sent = notification.sent_telegram
                sl = await db.scalar(
                    select(SearchListing).where(
                        SearchListing.search_id == search.id,
                        SearchListing.listing_id == listing_id,
                    )
                )
                if sl:
                    sl.notified_at = now_kyiv()

    return True, notification_sent


async def seed_search_baseline(
    db: AsyncSession,
    search: SearchQuery,
    items: list,
    *,
    limit: int = 40,
) -> int:
    """Прив’язує авто з першого пошуку до моніторингу без позначки «нове»."""
    from app.schemas.schemas import ListingOut
    from app.services.listings.upsert import upsert_listing

    linked = 0
    for raw in items[:limit]:
        try:
            data = raw if isinstance(raw, ListingOut) else ListingOut.model_validate(raw)
        except Exception:
            continue
        listing = await upsert_listing(db, data)
        created, _ = await link_listing_to_search(
            db,
            search=search,
            listing_id=listing.id,
            notify=False,
            user=None,
            mark_as_new=False,
        )
        if created:
            linked += 1
    await db.flush()
    return linked
