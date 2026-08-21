"""Алерти: значне зниження ціни / з’явився VIN для оголошень у збережених пошуках."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import now_kyiv
from app.models.models import Listing, Notification, NotificationType, SearchListing, SearchQuery, User
from app.services.currency import convert_price, format_display_price, listing_price_uah
from app.services.listings.price_drop import (
    MIN_SIGNIFICANT_PRICE_DROP_PERCENT,
    PRICE_DROP_NOTIFY_COOLDOWN_DAYS,
    format_drop_percent,
)
from app.services.parser.filter_groups import search_monitor_display_name
from app.services.telegram.client import SOURCE_LABELS, telegram_client
from app.services.telegram_channels.mapper import fix_telegram_listing_url

logger = logging.getLogger(__name__)


def _listing_card_data(listing: Listing) -> dict:
    from app.services.telegram.media_urls import filter_existing_image_urls

    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    display_currency = "USD"
    images = filter_existing_image_urls(listing.images)[:1]
    listing_url = (
        fix_telegram_listing_url(listing.id, listing.url, images=images)
        if source == "telegram"
        else listing.url
    )
    price_label = format_display_price(listing.price, listing.currency, display_currency)
    if source == "telegram" and not images:
        from app.services.telegram_channels.lazy_photos import (
            load_existing_telegram_photo_urls,
        )

        images = load_existing_telegram_photo_urls(listing.id, limit=1)

    return {
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


async def _send_event_card(
    user: User,
    listing: Listing,
    search: SearchQuery,
    *,
    alert_line: str,
    alert_emoji: str,
) -> bool:
    if not (user.telegram_connected and user.telegram_id):
        return False
    try:
        result = await telegram_client.send_listing_card(
            user.telegram_id,
            _listing_card_data(listing),
            search_monitor_display_name(search),
            search_id=search.id,
            listing_id=listing.id,
            alert_line=alert_line,
            alert_emoji=alert_emoji,
        )
        return bool(result)
    except Exception:
        logger.debug("listing event telegram failed", exc_info=True)
        return False


async def should_notify_price_drop(
    db: AsyncSession,
    *,
    user_id: str,
    search_id: str,
    listing_id: str,
    new_price: int,
    new_currency: str,
    drop_percent: float | None,
) -> bool:
    """Сповіщаємо лише про зниження ≥5% і не дублюємо дрібні коливання протягом cooldown."""
    if drop_percent is None or drop_percent < MIN_SIGNIFICANT_PRICE_DROP_PERCENT:
        return False

    since = now_kyiv() - timedelta(days=PRICE_DROP_NOTIFY_COOLDOWN_DAYS)
    previous = await db.scalar(
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.search_id == search_id,
            Notification.listing_id == listing_id,
            Notification.type == NotificationType.price_drop,
            Notification.created_at >= since,
        )
        .order_by(desc(Notification.created_at))
        .limit(1)
    )
    if not previous:
        return True

    payload = previous.payload or {}
    prev_new_price = payload.get("new_price")
    if prev_new_price is None:
        return True

    try:
        prev_new_price = int(prev_new_price)
    except (TypeError, ValueError):
        return True

    prev_currency = str(payload.get("currency") or new_currency)
    prev_uah = listing_price_uah(prev_new_price, prev_currency)
    new_uah = listing_price_uah(new_price, new_currency)
    if new_uah >= prev_uah:
        return False

    additional_drop = (prev_uah - new_uah) / prev_uah * 100 if prev_uah else 0
    return additional_drop >= MIN_SIGNIFICANT_PRICE_DROP_PERCENT


async def notify_listing_events(
    db: AsyncSession,
    listing: Listing,
    *,
    price_dropped: bool,
    old_price: int | None,
    old_currency: str | None,
    drop_percent: float | None,
    vin_appeared: bool,
) -> int:
    if not price_dropped and not vin_appeared:
        return 0

    rows = (
        await db.execute(
            select(SearchListing, SearchQuery, User)
            .join(SearchQuery, SearchQuery.id == SearchListing.search_id)
            .join(User, User.id == SearchQuery.user_id)
            .where(
                SearchListing.listing_id == listing.id,
                SearchQuery.is_active.is_(True),
            )
        )
    ).all()

    sent = 0
    for _sl, search, user in rows:
        display_currency = "USD"
        if price_dropped and old_price is not None:
            if not await should_notify_price_drop(
                db,
                user_id=user.id,
                search_id=search.id,
                listing_id=listing.id,
                new_price=int(listing.price or 0),
                new_currency=listing.currency or "USD",
                drop_percent=drop_percent,
            ):
                continue

            old_label = format_display_price(old_price, old_currency or listing.currency, display_currency)
            new_label = format_display_price(listing.price, listing.currency, display_currency)
            old_usd = convert_price(old_price, old_currency or listing.currency, display_currency)
            new_usd = convert_price(listing.price, listing.currency, display_currency)
            if new_usd >= old_usd:
                logger.info(
                    "Skip price_drop for %s: display %s → %s (not a drop)",
                    listing.id,
                    old_label,
                    new_label,
                )
                continue

            percent_label = format_drop_percent(drop_percent or 0)
            body = f"Ціна знижена на {percent_label}%: {old_label} → {new_label}"
            notification = Notification(
                user_id=user.id,
                type=NotificationType.price_drop,
                title=listing.title,
                body=body,
                listing_id=listing.id,
                search_id=search.id,
                payload={
                    "event": "price_drop",
                    "old_price": old_price,
                    "new_price": listing.price,
                    "old_currency": old_currency or listing.currency,
                    "currency": listing.currency,
                    "drop_percent": drop_percent,
                    "url": listing.url,
                    "source": listing.source.value if hasattr(listing.source, "value") else str(listing.source),
                },
            )
            db.add(notification)
            sent += 1
            if await _send_event_card(
                user,
                listing,
                search,
                alert_line=body,
                alert_emoji="📉",
            ):
                notification.sent_telegram = True

        if vin_appeared and listing.vin:
            body = f"З’явився VIN: {listing.vin}"
            notification = Notification(
                user_id=user.id,
                type=NotificationType.vin_found,
                title=listing.title,
                body=body,
                listing_id=listing.id,
                search_id=search.id,
                payload={
                    "event": "vin_found",
                    "vin": listing.vin,
                    "url": listing.url,
                    "source": listing.source.value if hasattr(listing.source, "value") else str(listing.source),
                },
            )
            db.add(notification)
            sent += 1
            if await _send_event_card(
                user,
                listing,
                search,
                alert_line=body,
                alert_emoji="🔑",
            ):
                notification.sent_telegram = True

    if sent:
        await db.flush()
    return sent
