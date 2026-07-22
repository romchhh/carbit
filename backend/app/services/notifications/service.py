import asyncio
import logging
from datetime import timedelta

from sqlalchemy import asc, desc, exists, func, nulls_last, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import (
    Listing,
    Notification,
    NotificationType,
    SearchListing,
    SearchQuery,
    User,
)
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


def monitor_telegram_delivery_done(notification: Notification) -> bool:
    """Telegram доставлено або свідомо пропущено (дубль / вже слали) — не ретраїмо."""
    if notification.sent_telegram:
        return True
    payload = notification.payload or {}
    return bool(
        payload.get("telegram_skipped_duplicate")
        or payload.get("telegram_skipped_already_notified")
    )


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

    # Soft-match лише за VIN (brand/model/year без VIN — різні авто).
    vin = (getattr(listing, "vin", None) or "").strip().upper()
    if not vin or len(vin) != 17:
        return False

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
                func.upper(Listing.vin) == vin,
                Listing.id.notin_(list(family_ids)),
            )
            .limit(10)
        )
    ).all()
    return bool(recent)


async def _attempt_listing_match_telegram(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery | None,
    notification: Notification,
    *,
    skip_freshness_check: bool,
    max_published_hours: float | None,
) -> bool:
    """Надсилає картку в Telegram; оновлює notification.sent_telegram."""
    if not (user.telegram_connected and user.telegram_id):
        return False

    if max_published_hours is None:
        settings = await get_parser_settings()
        max_published_hours = coerce_notification_max_hours(
            settings.get("notification_max_published_hours", 1)
        )
    else:
        max_published_hours = coerce_notification_max_hours(max_published_hours)

    if not skip_freshness_check and not is_listing_fresh_for_notification(
        listing.published_at,
        max_hours=max_published_hours,
        allow_none=True,
    ):
        logger.info(
            "Skip Telegram notify for %s: published_at=%s max_hours=%s",
            listing.id,
            listing.published_at,
            max_published_hours,
        )
        return False

    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    listing_url = (
        fix_telegram_listing_url(listing.id, listing.url, images=listing.images)
        if source == "telegram"
        else listing.url
    )
    display_currency = "USD"
    price_label = format_display_price(listing.price, listing.currency, display_currency)

    images = list(listing.images or [])[:1]
    if source == "telegram" and not images:
        from app.services.telegram_channels.lazy_photos import load_existing_telegram_photo_urls

        images = load_existing_telegram_photo_urls(listing.id, limit=1)
        if images:
            listing.images = images
            await db.flush()

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
        "images": images,
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "url": listing_url,
    }
    search_name = search.name if search else "Carbit"
    result = None
    for attempt in range(2):
        result = await telegram_client.send_listing_card(
            user.telegram_id,
            listing_data,
            search_name,
            search_id=search.id if search else None,
            listing_id=listing.id,
        )
        if result:
            break
        if attempt == 0:
            await asyncio.sleep(0.6)
    if result:
        notification.sent_telegram = True
        await db.flush()
        return True

    logger.warning(
        "Telegram listing card failed user=%s listing=%s search=%s",
        user.id,
        listing.id,
        search.id if search else None,
    )
    return False


async def create_listing_notification(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery | None = None,
    send_telegram: bool = True,
    max_published_hours: float | None = None,
    skip_freshness_check: bool = False,
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
    skipped_duplicate = False
    skipped_already_notified = False
    if send_telegram and user.telegram_connected and user.telegram_id:
        # Дзеркало з тим самим VIN — у TG лише канонічна картка
        vin = (getattr(listing, "vin", None) or "").strip().upper()
        if (
            bool(getattr(listing, "is_duplicate", False))
            and getattr(listing, "duplicate_of", None)
            and len(vin) == 17
        ):
            skip_telegram = True
            skipped_duplicate = True
            logger.info("Skip Telegram notify for VIN-duplicate mirror %s", listing.id)
        elif await user_already_notified_for_car(db, user.id, listing):
            skip_telegram = True
            skipped_already_notified = True
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
            "telegram_skipped_duplicate": skipped_duplicate,
            "telegram_skipped_already_notified": skipped_already_notified,
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

        await _attempt_listing_match_telegram(
            db,
            user,
            listing,
            search,
            notification,
            skip_freshness_check=skip_freshness_check,
            max_published_hours=max_published_hours,
        )

    return notification


async def notify_monitor_listing_after_link(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery,
    *,
    sl: SearchListing,
) -> bool:
    """Telegram одразу після появи авто в моніторингу (skip freshness, повтор при збої)."""
    settings = await get_parser_settings()
    if not settings.get("notify_telegram", True):
        return False
    if not (user.telegram_connected and user.telegram_id):
        return False

    notification = await create_listing_notification(
        db,
        user,
        listing,
        search=search,
        max_published_hours=None,
        skip_freshness_check=True,
    )
    if not notification.sent_telegram and not monitor_telegram_delivery_done(notification):
        await _attempt_listing_match_telegram(
            db,
            user,
            listing,
            search,
            notification,
            skip_freshness_check=True,
            max_published_hours=None,
        )

    if monitor_telegram_delivery_done(notification):
        sl.notified_at = now_kyiv()
    return bool(notification.sent_telegram)


async def deliver_pending_monitor_telegram(
    db: AsyncSession,
    *,
    search_ids: list[str] | None = None,
    limit: int = 40,
) -> int:
    """Догоняє Telegram для «нових» авто в моніторингу, якщо перша спроба не вдалась."""
    settings = await get_parser_settings()
    if not settings.get("notify_telegram", True):
        return 0

    sent_subq = (
        select(Notification.id)
        .where(
            Notification.user_id == User.id,
            Notification.search_id == SearchListing.search_id,
            Notification.listing_id == SearchListing.listing_id,
            Notification.type == NotificationType.listing_match,
            Notification.sent_telegram.is_(True),
        )
        .limit(1)
    )
    unsent_notif_subq = (
        select(Notification.id)
        .where(
            Notification.user_id == User.id,
            Notification.search_id == SearchListing.search_id,
            Notification.listing_id == SearchListing.listing_id,
            Notification.type == NotificationType.listing_match,
            Notification.sent_telegram.is_(False),
        )
        .limit(1)
    )

    stmt = (
        select(SearchListing, SearchQuery, User, Listing)
        .join(SearchQuery, SearchQuery.id == SearchListing.search_id)
        .join(User, User.id == SearchQuery.user_id)
        .join(Listing, Listing.id == SearchListing.listing_id)
        .where(
            or_(SearchListing.is_new.is_(True), exists(unsent_notif_subq)),
            SearchQuery.is_active.is_(True),
            User.telegram_connected.is_(True),
            User.telegram_id.isnot(None),
            ~exists(sent_subq),
        )
        .limit(max(1, limit))
    )
    if search_ids:
        stmt = stmt.where(SearchQuery.id.in_(search_ids))

    rows = (await db.execute(stmt)).all()
    delivered = 0
    for sl, search, user, listing in rows:
        latest = await db.scalar(
            select(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.search_id == search.id,
                Notification.listing_id == listing.id,
                Notification.type == NotificationType.listing_match,
            )
            .order_by(desc(Notification.created_at))
            .limit(1)
        )
        if latest and latest.sent_telegram:
            sl.notified_at = now_kyiv()
            delivered += 1
            continue
        if latest and monitor_telegram_delivery_done(latest):
            sl.notified_at = now_kyiv()
            continue
        if latest:
            ok = await _attempt_listing_match_telegram(
                db,
                user,
                listing,
                search,
                latest,
                skip_freshness_check=True,
                max_published_hours=None,
            )
            if ok:
                delivered += 1
            if ok or monitor_telegram_delivery_done(latest):
                sl.notified_at = now_kyiv()
            continue

        notification = await create_listing_notification(
            db,
            user,
            listing,
            search=search,
            skip_freshness_check=True,
        )
        if monitor_telegram_delivery_done(notification):
            sl.notified_at = now_kyiv()
        if notification.sent_telegram:
            delivered += 1

    if delivered:
        await db.flush()
        logger.info(
            "Delivered %s pending monitor Telegram notification(s) search_ids=%s",
            delivered,
            search_ids,
        )
    return delivered


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
