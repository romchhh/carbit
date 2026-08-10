import asyncio
import logging
from datetime import timedelta

from sqlalchemy import asc, desc, exists, func, nulls_last, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sqlite_retry import commit_session, flush_session
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
from app.services.parser.filter_groups import (
    listing_matches_search_query,
    search_monitor_display_name,
)
from app.services.parser.settings import get_parser_settings
from app.services.listings.duplicates import listings_look_same, listing_vin_for_dedup
from app.services.telegram.client import telegram_client, SOURCE_LABELS
from app.services.telegram_channels.mapper import fix_telegram_listing_url

logger = logging.getLogger(__name__)


def monitor_telegram_delivery_done(notification: Notification) -> bool:
    """Telegram доставлено — повторна догонка не потрібна."""
    return bool(notification.sent_telegram)


async def _duplicate_family_ids(db: AsyncSession, listing: Listing) -> set[str]:
    """ID оголошення + VIN-дзеркала (лише при валідному VIN)."""
    ids = {listing.id}
    vin = listing_vin_for_dedup(listing)
    if not vin:
        return ids

    parent_id = getattr(listing, "duplicate_of", None)
    if parent_id:
        parent = await db.get(Listing, parent_id)
        if parent and listings_look_same(listing, parent):
            ids.add(parent_id)

    rows = (
        await db.scalars(
            select(Listing).where(
                or_(
                    Listing.duplicate_of == listing.id,
                    Listing.duplicate_of.in_(list(ids)),
                    Listing.id.in_(list(ids)),
                )
            ).limit(80)
        )
    ).all()
    for row in rows:
        if listings_look_same(listing, row):
            ids.add(row.id)
    return ids


async def user_already_notified_for_car(
    db: AsyncSession,
    user_id: str,
    listing: Listing,
    *,
    lookback_hours: int = 72,
) -> bool:
    """True, якщо юзеру вже успішно слали TG по цьому VIN (або VIN-дзеркалу)."""
    vin = listing_vin_for_dedup(listing)
    if not vin:
        return False

    family_ids = await _duplicate_family_ids(db, listing)
    if await db.scalar(
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.type == NotificationType.listing_match,
            Notification.listing_id.in_(list(family_ids)),
            Notification.sent_telegram.is_(True),
        )
        .limit(1)
    ):
        return True

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


def _listing_source_label(listing: Listing) -> str:
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    return SOURCE_LABELS.get(source, source)


async def _vin_family_source_labels(db: AsyncSession, listing: Listing) -> list[str]:
    family = await _duplicate_family_ids(db, listing)
    if len(family) <= 1:
        return [_listing_source_label(listing)]
    rows = (await db.scalars(select(Listing).where(Listing.id.in_(list(family))))).all()
    labels = sorted({_listing_source_label(row) for row in rows})
    return labels


async def _prior_telegram_source_labels(
    db: AsyncSession,
    user_id: str,
    listing: Listing,
) -> list[str]:
    """Джерела, з яких юзеру вже успішно відправляли TG по VIN-сімʼї (інші listing_id)."""
    family = await _duplicate_family_ids(db, listing)
    other_ids = family - {listing.id}
    if not other_ids:
        return []
    rows = (
        await db.scalars(
            select(Listing)
            .join(Notification, Notification.listing_id == Listing.id)
            .where(
                Notification.user_id == user_id,
                Notification.type == NotificationType.listing_match,
                Notification.sent_telegram.is_(True),
                Listing.id.in_(list(other_ids)),
            )
        )
    ).all()
    labels: list[str] = []
    seen: set[str] = set()
    for listing_row in rows:
        label = _listing_source_label(listing_row)
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


async def build_cross_source_telegram_alert(
    db: AsyncSession,
    user_id: str,
    listing: Listing,
) -> tuple[str | None, str]:
    """Текст для TG: дубль з іншого джерела або одразу кілька джерел."""
    current = _listing_source_label(listing)
    prior = await _prior_telegram_source_labels(db, user_id, listing)
    if prior:
        prev = ", ".join(prior)
        return (
            f"Це авто вже знайдено на {prev}. Ось оголошення з {current}.",
            "🔗",
        )
    family_labels = await _vin_family_source_labels(db, listing)
    if len(family_labels) > 1:
        names = ", ".join(family_labels)
        return (f"Знайдено одразу на кількох джерелах: {names}.", "🔗")
    return None, "🚗"


async def _attempt_listing_match_telegram(
    db: AsyncSession,
    user: User,
    listing: Listing,
    search: SearchQuery | None,
    notification: Notification,
    *,
    skip_freshness_check: bool,
    max_published_hours: float | None,
    alert_line: str | None = None,
    alert_emoji: str = "🚗",
) -> bool:
    """Надсилає картку в Telegram; оновлює notification.sent_telegram."""
    if not (user.telegram_connected and user.telegram_id):
        return False

    if max_published_hours is None:
        settings = await get_parser_settings()
        max_published_hours = coerce_notification_max_hours(
            settings.get("notification_max_published_hours", 6)
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
    from app.services.telegram.media_urls import filter_existing_image_urls

    images = filter_existing_image_urls(listing.images)[:1]
    listing_url = (
        fix_telegram_listing_url(listing.id, listing.url, images=images)
        if source == "telegram"
        else listing.url
    )
    display_currency = "USD"
    price_label = format_display_price(listing.price, listing.currency, display_currency)

    if source == "telegram" and not images:
        from app.services.telegram_channels.lazy_photos import load_existing_telegram_photo_urls

        images = load_existing_telegram_photo_urls(listing.id, limit=1)
        if images:
            listing.images = images
            await flush_session(db)

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
    search_name = search_monitor_display_name(search) if search else "Carbit"
    result = None
    for attempt in range(2):
        result = await telegram_client.send_listing_card(
            user.telegram_id,
            listing_data,
            search_name,
            search_id=search.id if search else None,
            listing_id=listing.id,
            alert_line=alert_line,
            alert_emoji=alert_emoji,
        )
        if result:
            break
        if attempt == 0:
            await asyncio.sleep(0.6)
    if result:
        notification.sent_telegram = True
        await flush_session(db)
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
    skipped_no_chat_id = False
    cross_source_alert: str | None = None
    cross_source_emoji = "🚗"

    if not (user.telegram_connected and user.telegram_id):
        skip_telegram = True
        skipped_no_chat_id = True
        if user.telegram_connected and not user.telegram_id:
            logger.warning(
                "User %s has telegram_connected=True but telegram_id=None — needs /start in bot",
                user.id,
            )
    elif send_telegram:
        cross_source_alert, cross_source_emoji = await build_cross_source_telegram_alert(
            db, user.id, listing
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
            "telegram_skipped_no_chat_id": skipped_no_chat_id,
            "cross_source_alert": cross_source_alert,
        },
    )
    db.add(notification)
    await flush_session(db)

    if (
        send_telegram
        and not skip_telegram
        and user.telegram_connected
        and user.telegram_id
    ):
        if max_published_hours is None:
            settings = await get_parser_settings()
            max_published_hours = coerce_notification_max_hours(
                settings.get("notification_max_published_hours", 6)
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
            alert_line=cross_source_alert,
            alert_emoji=cross_source_emoji,
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
    """Telegram одразу після появи свіжого «нового» авто в моніторингу."""
    settings = await get_parser_settings()
    if not settings.get("notify_telegram", True):
        return False

    if not listing_matches_search_query(listing, search):
        logger.info(
            "Skip monitor Telegram: listing %s does not match search %s filters",
            listing.id,
            search.id,
        )
        return False

    max_hours = coerce_notification_max_hours(
        settings.get("notification_max_published_hours", 6)
    )
    if not is_listing_fresh_for_notification(
        listing.published_at,
        max_hours=max_hours,
        allow_none=False,
    ):
        return False

    notification = await create_listing_notification(
        db,
        user,
        listing,
        search=search,
        max_published_hours=max_hours,
        skip_freshness_check=False,
    )
    if not notification.sent_telegram and not monitor_telegram_delivery_done(notification):
        if user.telegram_connected and user.telegram_id:
            alert_line = (notification.payload or {}).get("cross_source_alert")
            alert_emoji = "🔗" if alert_line else "🚗"
            if alert_line is None:
                alert_line, alert_emoji = await build_cross_source_telegram_alert(
                    db, user.id, listing
                )
            await _attempt_listing_match_telegram(
                db,
                user,
                listing,
                search,
                notification,
                skip_freshness_check=False,
                max_published_hours=max_hours,
                alert_line=alert_line,
                alert_emoji=alert_emoji,
            )

    if monitor_telegram_delivery_done(notification):
        sl.notified_at = now_kyiv()
    return bool(notification.sent_telegram)


async def deliver_pending_monitor_telegram(
    db: AsyncSession,
    *,
    search_ids: list[str] | None = None,
    limit: int = 40,
    persist_each: bool = False,
) -> int:
    """Догоняє Telegram лише для непереглянутих (is_new) свіжих авто в моніторингу."""
    settings = await get_parser_settings()
    if not settings.get("notify_telegram", True):
        return 0

    max_hours = coerce_notification_max_hours(
        settings.get("notification_max_published_hours", 6)
    )

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
    stmt = (
        select(SearchListing, SearchQuery, User, Listing)
        .join(SearchQuery, SearchQuery.id == SearchListing.search_id)
        .join(User, User.id == SearchQuery.user_id)
        .join(Listing, Listing.id == SearchListing.listing_id)
        .where(
            SearchListing.is_new.is_(True),
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
        if persist_each:
            await commit_session(db)

        if not is_listing_fresh_for_notification(
            listing.published_at,
            max_hours=max_hours,
            allow_none=False,
        ):
            sl.is_new = False
            search.new_count = max(0, (search.new_count or 0) - 1)
            await flush_session(db)
            if persist_each:
                await commit_session(db)
            continue

        if not listing_matches_search_query(listing, search):
            logger.info(
                "Drop stale monitor link: listing %s not matching search %s",
                listing.id,
                search.id,
            )
            sl.is_new = False
            search.new_count = max(0, (search.new_count or 0) - 1)
            await flush_session(db)
            if persist_each:
                await commit_session(db)
            continue

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
            await flush_session(db)
            if persist_each:
                await commit_session(db)
            continue
        if latest and monitor_telegram_delivery_done(latest):
            sl.notified_at = now_kyiv()
            await flush_session(db)
            if persist_each:
                await commit_session(db)
            continue
        if latest:
            payload = latest.payload or {}
            alert_line = payload.get("cross_source_alert")
            alert_emoji = "🔗" if alert_line else "🚗"
            if alert_line is None:
                alert_line, alert_emoji = await build_cross_source_telegram_alert(
                    db, user.id, listing
                )
            ok = await _attempt_listing_match_telegram(
                db,
                user,
                listing,
                search,
                latest,
                skip_freshness_check=False,
                max_published_hours=max_hours,
                alert_line=alert_line,
                alert_emoji=alert_emoji,
            )
            if ok:
                delivered += 1
            if ok or monitor_telegram_delivery_done(latest):
                sl.notified_at = now_kyiv()
            await flush_session(db)
            if persist_each:
                await commit_session(db)
            continue

        notification = await create_listing_notification(
            db,
            user,
            listing,
            search=search,
            skip_freshness_check=False,
            max_published_hours=max_hours,
        )
        if monitor_telegram_delivery_done(notification):
            sl.notified_at = now_kyiv()
        if notification.sent_telegram:
            delivered += 1

        await flush_session(db)
        if persist_each:
            await commit_session(db)

    if delivered:
        if not persist_each:
            await flush_session(db)
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
