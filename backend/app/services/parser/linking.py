from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import Listing, SearchListing, SearchQuery, User
from app.services.notifications.service import create_listing_notification


async def link_listing_to_search(
    db: AsyncSession,
    *,
    search: SearchQuery,
    listing_id: str,
    notify: bool,
    user: User | None,
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
            notification = await create_listing_notification(db, user, listing, search=search)
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
