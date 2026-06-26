from datetime import datetime, UTC

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification, NotificationType, User, Listing, SearchQuery
from app.services.telegram.client import telegram_client


async def create_listing_notification(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery | None = None,
    send_telegram: bool = True,
) -> Notification:
    source_labels = {"auto_ria": "AUTO.RIA", "olx": "OLX", "telegram": "Telegram"}
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)

    notification = Notification(
        user_id=user.id,
        type=NotificationType.listing_match,
        title=listing.title,
        body=f"{listing.year} · {listing.mileage:,} км · {listing.price:,} грн · {listing.region}",
        listing_id=listing.id,
        search_id=search.id if search else None,
        payload={
            "price": listing.price,
            "year": listing.year,
            "mileage": listing.mileage,
            "region": listing.region,
            "source": source,
            "source_label": source_labels.get(source, source),
            "url": listing.url,
        },
    )
    db.add(notification)
    await db.flush()

    if send_telegram and user.telegram_connected and user.telegram_id:
        listing_data = {
            "title": listing.title,
            "year": listing.year,
            "mileage": listing.mileage,
            "price": listing.price,
            "currency": listing.currency,
            "region": listing.region,
            "source": source,
            "source_label": source_labels.get(source, source),
            "url": listing.url,
        }
        search_name = search.name if search else "Carbit"
        result = await telegram_client.send_listing_card(user.telegram_id, listing_data, search_name)
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
    result = await db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    count = 0
    for n in result.all():
        n.is_read = True
        count += 1
    await db.flush()
    return count
