import logging
from datetime import timedelta

from sqlalchemy import asc, desc, func, nulls_last, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
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


async def _duplicate_family_ids(db: AsyncSession, listing: Listing) -> set[str]:
    """ID цього оголошення + канон / дзеркала через duplicate_of."""
    ids = {listing.id}
    parent = getattr(listing, "duplicate_of", None)
    if parent:
        ids.add(parent)
    rows = (
        await db.scalars(
            select(Listing.id).where(
                or_(
                    Listing.id.in_(list(ids)),
                    Listing.duplicate_of.in_(list(ids)),
                    Listing.duplicate_of == listing.id,
                )
            )
        )
    ).all()
    ids.update(rows)
    return ids


async def user_already_notified_for_car(
    db: AsyncSession,
    user_id: str,
    listing: Listing,
    *,
    lookback_hours: int = 72,
) -> bool:
    """True, якщо юзеру вже слали listing_match по цьому авто / дзеркалу / двійнику."""
    family_ids = await _duplicate_family_ids(db, listing)
    exact = await db.scalar(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.type == NotificationType.listing_match,
            Notification.listing_id.in_(list(family_ids)),
            Notification.sent_telegram.is_(True),
        ).limit(1)
    )
    if exact:
        return True

    # Soft-match: те саме авто під іншим listing_id (OLX repost / інше джерело без duplicate_of).
    brand = (listing.brand or "").strip()
    model = (listing.model or "").strip()
    year = int(listing.year or 0)
    if not brand or not model or not year:
        return False

    from app.services.listings.duplicates import listings_look_same

    since = now_kyiv() - timedelta(hours=max(1, lookback_hours))
    recent = (
        await db.scalars(
            select(Listing)
            .join(Notification, Notification.listing_id == Listing.id)
            .where(
                Notification.user_id == user_id,
                Notification.type == NotificationType.listing_match,
                Notification.sent_telegram.is_(True),
                Notification.created_at >= since,
                Listing.brand == brand,
                Listing.model == model,
                Listing.year == year,
                Listing.id.notin_(list(family_ids)),
            )
            .limit(40)
        )
    ).all()
    for other in recent:
        if listings_look_same(listing, other):
            return True
    return False


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

    skip_telegram = False
    if send_telegram and user.telegram_connected and user.telegram_id:
        # Дзеркало іншого джерела — у TG лише канонічна картка
        if bool(getattr(listing, "is_duplicate", False)):
            skip_telegram = True
            logger.info("Skip Telegram notify for duplicate mirror %s", listing.id)
        elif await user_already_notified_for_car(db, user.id, listing):
            skip_telegram = True
            logger.info(
                "Skip Telegram notify for %s: user %s already notified for this car",
                listing.id,
                user.id,
            )

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
            "telegram_skipped_duplicate": skip_telegram,
        },
    )
    db.add(notification)
    await db.flush()

    if (
        send_telegram
        and not skip_telegram
        and user.telegram_connected
        and user.telegram_id
    ):
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


def notification_to_out(
    notification: Notification,
    listing: Listing | None = None,
    *,
    listing_out=None,
) -> NotificationOut:
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
        listing=listing_out if listing_out is not None else (listing_to_out(listing) if listing else None),
    )


async def notification_to_out_with_mirrors(
    db: AsyncSession,
    notification: Notification,
    listing: Listing | None = None,
) -> NotificationOut:
    from app.services.listings.duplicates import listing_out_with_mirrors

    listing_out = await listing_out_with_mirrors(db, listing) if listing else None
    return notification_to_out(notification, listing, listing_out=listing_out)


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
    items = [
        await notification_to_out_with_mirrors(db, n, listing)
        for n, listing in rows
    ]
    return items, int(total), unread
