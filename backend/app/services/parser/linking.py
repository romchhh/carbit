from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import Listing, SearchListing, SearchQuery, User
from app.services.notifications.freshness import is_listing_fresh_for_notification
from app.services.notifications.service import notify_monitor_listing_after_link


async def link_listing_to_search(
    db: AsyncSession,
    *,
    search: SearchQuery,
    listing_id: str,
    notify: bool,
    user: User | None,
    max_notification_hours: float | None = None,
    mark_as_new: bool = True,
    publish_immediately: bool = False,  # caller commits after the batch
) -> tuple[bool, bool]:
    """Returns (linked_newly, notification_sent).

    linked_newly — перший раз прив’язали oголошення до пошуку.
    «Нове» / Telegram — лише якщо mark_as_new і published_at у вікні max_notification_hours.
    """
    del publish_immediately  # unused: caller commits

    listing = await db.get(Listing, listing_id)

    if mark_as_new and max_notification_hours is not None and listing:
        if not is_listing_fresh_for_notification(
            listing.published_at,
            max_hours=max_notification_hours,
            allow_none=False,
        ):
            mark_as_new = False
            notify = False

    existing = await db.scalar(
        select(SearchListing).where(
            SearchListing.search_id == search.id,
            SearchListing.listing_id == listing_id,
        )
    )
    if existing:
        return False, False

    sl = SearchListing(
        search_id=search.id,
        listing_id=listing_id,
        is_new=mark_as_new,
        first_seen_at=now_kyiv(),
    )
    db.add(sl)
    if mark_as_new:
        search.new_count = (search.new_count or 0) + 1
    search.total_count = (search.total_count or 0) + 1
    search.last_checked_at = now_kyiv()
    await db.flush()

    notification_sent = False
    if mark_as_new and notify:
        owner = user if user and user.id == search.user_id else await db.get(User, search.user_id)
        if owner and listing:
            notification_sent = await notify_monitor_listing_after_link(
                db,
                owner,
                listing,
                search,
                sl=sl,
            )

    return True, notification_sent


async def seed_search_baseline(
    db: AsyncSession,
    search: SearchQuery,
    items: list,
    *,
    limit: int = 40,
) -> int:
    """Прив’язує авто з першого пошуку до моніторингу без позначки «нове».

    Також upsert-ить `alternate_sources`, щоб у БД були дзеркала для іконок джерел.
    """
    from app.schemas.schemas import ListingOut
    from app.services.listings.upsert import upsert_listing_with_mirrors

    linked = 0
    for raw in items[:limit]:
        try:
            data = raw if isinstance(raw, ListingOut) else ListingOut.model_validate(raw)
        except Exception:
            continue
        listing = await upsert_listing_with_mirrors(db, data)
        created, _ = await link_listing_to_search(
            db,
            search=search,
            listing_id=listing.id,
            notify=False,
            user=None,
            mark_as_new=False,
            publish_immediately=False,
        )
        if created:
            linked += 1
    await db.flush()
    return linked
