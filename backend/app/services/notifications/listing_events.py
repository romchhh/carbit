"""Алерти: ціна впала / з’явився VIN для оголошень у збережених пошуках."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Notification, NotificationType, SearchListing, SearchQuery, User
from app.services.currency import format_display_price
from app.services.parser.filter_groups import search_monitor_display_name
from app.services.telegram.client import SOURCE_LABELS, telegram_client
from app.services.telegram_channels.mapper import fix_telegram_listing_url

logger = logging.getLogger(__name__)


def _listing_card_data(listing: Listing) -> dict:
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    display_currency = "USD"
    listing_url = (
        fix_telegram_listing_url(listing.id, listing.url, images=listing.images)
        if source == "telegram"
        else listing.url
    )
    price_label = format_display_price(listing.price, listing.currency, display_currency)
    images = list(listing.images or [])[:1]
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


async def notify_listing_events(
    db: AsyncSession,
    listing: Listing,
    *,
    price_dropped: bool,
    old_price: int | None,
    old_currency: str | None,
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
        # Telegram-алерти завжди в $
        display_currency = "USD"
        if price_dropped and old_price is not None:
            old_label = format_display_price(old_price, old_currency or listing.currency, display_currency)
            new_label = format_display_price(listing.price, listing.currency, display_currency)
            # Захист: якщо в $ нова ≥ старої — це не зниження (зміна валюти / шум курсу)
            from app.services.currency import convert_price

            old_usd = convert_price(old_price, old_currency or listing.currency, display_currency)
            new_usd = convert_price(listing.price, listing.currency, display_currency)
            if new_usd >= old_usd:
                logger.info(
                    "Skip price_drop for %s: display %s → %s (not a drop)",
                    listing.id,
                    old_label,
                    new_label,
                )
            else:
                body = f"Ціна знизилась: {old_label} → {new_label}"
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
