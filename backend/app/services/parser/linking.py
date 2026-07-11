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
) -> tuple[bool, bool]:
    """Returns (is_new, notification_sent)."""
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
            is_new=True,
            first_seen_at=now_kyiv(),
        )
    )
    search.new_count = (search.new_count or 0) + 1
    search.total_count = (search.total_count or 0) + 1
    search.last_checked_at = now_kyiv()

    notification_sent = False
    if notify and user and user.telegram_connected:
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
