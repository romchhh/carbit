import logging

from sqlalchemy import asc, desc, func, nulls_last, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification, NotificationType, User, Listing, SearchQuery
from app.schemas.schemas import NotificationOut
from app.services.currency import format_display_price
from app.services.listings.serialize import listing_to_out
from app.services.notifications.freshness import (
    coerce_notification_max_hours,
    is_listing_fresh_for_notification,
)
from app.services.parser.settings import get_parser_settings
from app.services.telegram.client import telegram_client, SOURCE_LABELS
from app.services.telegram_channels.mapper import fix_telegram_listing_url

logger = logging.getLogger(__name__)


async def create_listing_notification(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery | None = None,
    send_telegram: bool = True,
    max_published_hours: float | None = None,
) -> Notification:
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    listing_url = (
        fix_telegram_listing_url(listing.id, listing.url, images=listing.images)
        if source == "telegram"
        else listing.url
    )

    # Telegram-картки завжди в $ (основна валюта продукту)
    display_currency = "USD"
    price_label = format_display_price(listing.price, listing.currency, display_currency)

    notification = Notification(
        user_id=user.id,
        type=NotificationType.listing_match,
        title=listing.title,
        body=f"{listing.year} · {listing.mileage:,} км · {price_label} · {listing.region}",
        listing_id=listing.id,
        search_id=search.id if search else None,
        payload={
            "price": listing.price,
            "display_price": price_label,
            "preferred_currency": display_currency,
            "year": listing.year,
            "mileage": listing.mileage,
            "region": listing.region,
            "source": source,
            "source_label": SOURCE_LABELS.get(source, source),
            "url": listing_url,
            "fuel": listing.fuel,
            "transmission": listing.transmission,
        },
    )
    db.add(notification)
    await db.flush()

    if send_telegram and user.telegram_connected and user.telegram_id:
        if max_published_hours is None:
            settings = await get_parser_settings()
            max_published_hours = coerce_notification_max_hours(
                settings.get("notification_max_published_hours", 1)
            )
        else:
            max_published_hours = coerce_notification_max_hours(max_published_hours)

        if not is_listing_fresh_for_notification(
            listing.published_at,
            max_hours=max_published_hours,
        ):
            logger.info(
                "Skip Telegram notify for %s: published_at=%s max_hours=%s",
                listing.id,
                listing.published_at,
                max_published_hours,
            )
        else:
            listing_data = {
                "title": listing.title,
                "year": listing.year,
                "mileage": listing.mileage,
                "price": listing.price,
                "currency": listing.currency,
                "display_price": price_label,
                "preferred_currency": display_currency,
                "region": listing.region,
                "fuel": listing.fuel,
                "transmission": listing.transmission,
                "description": listing.description,
                "images": list(listing.images or []),
                "published_at": listing.published_at.isoformat() if listing.published_at else None,
                "source": source,
                "source_label": SOURCE_LABELS.get(source, source),
                "url": listing_url,
            }
            search_name = search.name if search else "Carbit"
            result = await telegram_client.send_listing_card(
                user.telegram_id,
                listing_data,
                search_name,
                search_id=search.id if search else None,
                listing_id=listing.id,
            )
            if result:
                notification.sent_telegram = True
                await db.flush()

    return notification


async def get_unread_count(db: AsyncSession, user_id: str) -> int:
    return await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ) or 0


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.flush()
    return int(getattr(result, "rowcount", 0) or 0)


def notification_to_out(notification: Notification, listing: Listing | None = None) -> NotificationOut:
    ntype = notification.type.value if hasattr(notification.type, "value") else str(notification.type)
    return NotificationOut(
        id=notification.id,
        type=ntype,
        title=notification.title,
        body=notification.body,
        listing_id=notification.listing_id,
        search_id=notification.search_id,
        payload=notification.payload or {},
        is_read=notification.is_read,
        sent_telegram=notification.sent_telegram,
        created_at=notification.created_at,
        listing=listing_to_out(listing) if listing else None,
    )


def _notification_order_by(sort_by: str):
    if sort_by == "price_asc":
        return (nulls_last(asc(Listing.price)), desc(Notification.created_at))
    if sort_by == "price_desc":
        return (nulls_last(desc(Listing.price)), desc(Notification.created_at))
    if sort_by == "year_desc":
        return (nulls_last(desc(Listing.year)), desc(Notification.created_at))
    if sort_by == "mileage_asc":
        return (nulls_last(asc(Listing.mileage)), desc(Notification.created_at))
    return (desc(Notification.created_at),)


async def list_user_notifications(
    db: AsyncSession,
    user_id: str,
    *,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
    sort_by: str = "newest",
) -> tuple[list[NotificationOut], int, int]:
    filters = [Notification.user_id == user_id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))

    total = (
        await db.scalar(
            select(func.count()).select_from(Notification).where(*filters)
        )
        or 0
    )
    unread = await get_unread_count(db, user_id)

    offset = max(page - 1, 0) * per_page
    stmt = (
        select(Notification, Listing)
        .outerjoin(Listing, Notification.listing_id == Listing.id)
        .where(*filters)
        .order_by(*_notification_order_by(sort_by))
        .offset(offset)
        .limit(per_page)
    )
    rows = (await db.execute(stmt)).all()
    items = [notification_to_out(n, listing) for n, listing in rows]
    return items, int(total), unread
