import asyncio
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification, NotificationType, User, Listing, SearchQuery
from app.schemas.schemas import NotificationOut
from app.services.listings.serialize import listing_to_out
from app.services.telegram.client import telegram_client, SOURCE_LABELS


async def create_listing_notification(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery | None = None,
    send_telegram: bool = True,
) -> Notification:
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
            "source_label": SOURCE_LABELS.get(source, source),
            "url": listing.url,
            "fuel": listing.fuel,
            "transmission": listing.transmission,
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
            "fuel": listing.fuel,
            "transmission": listing.transmission,
            "description": listing.description,
            "images": list(listing.images or []),
            "source": source,
            "source_label": SOURCE_LABELS.get(source, source),
            "url": listing.url,
        }
        search_name = search.name if search else "Carbit"
        await asyncio.sleep(random.uniform(1, 3))
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


def _sort_notification_rows(
    rows: list[tuple[Notification, Listing | None]],
    sort_by: str,
) -> list[tuple[Notification, Listing | None]]:
    if sort_by == "price_asc":
        return sorted(rows, key=lambda row: row[1].price if row[1] else 0)
    if sort_by == "price_desc":
        return sorted(rows, key=lambda row: row[1].price if row[1] else 0, reverse=True)
    if sort_by == "year_desc":
        return sorted(rows, key=lambda row: row[1].year if row[1] else 0, reverse=True)
    if sort_by == "mileage_asc":
        return sorted(rows, key=lambda row: row[1].mileage if row[1] else 0)
    return sorted(rows, key=lambda row: row[0].created_at, reverse=True)


async def list_user_notifications(
    db: AsyncSession,
    user_id: str,
    *,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
    sort_by: str = "newest",
) -> tuple[list[NotificationOut], int, int]:
    stmt = (
        select(Notification, Listing)
        .outerjoin(Listing, Notification.listing_id == Listing.id)
        .where(Notification.user_id == user_id)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    rows = (await db.execute(stmt)).all()
    sorted_rows = _sort_notification_rows(list(rows), sort_by)
    total = len(sorted_rows)
    unread = await get_unread_count(db, user_id)

    start = (page - 1) * per_page
    page_rows = sorted_rows[start : start + per_page]
    items = [notification_to_out(n, listing) for n, listing in page_rows]
    return items, total, unread
