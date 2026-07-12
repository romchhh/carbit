"""Алерти: ціна впала / з’явився VIN для оголошень у збережених пошуках."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Notification, NotificationType, SearchListing, SearchQuery, User
from app.services.currency import format_display_price, resolve_display_currency
from app.services.telegram.client import telegram_client

logger = logging.getLogger(__name__)


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
        display_currency = resolve_display_currency(getattr(user, "preferred_currency", None))
        if price_dropped and old_price is not None:
            old_label = format_display_price(old_price, old_currency or listing.currency, display_currency)
            new_label = format_display_price(listing.price, listing.currency, display_currency)
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
                    "currency": listing.currency,
                    "url": listing.url,
                    "source": listing.source.value if hasattr(listing.source, "value") else str(listing.source),
                },
            )
            db.add(notification)
            sent += 1
            if user.telegram_connected and user.telegram_id:
                try:
                    await telegram_client.send_message(
                        user.telegram_id,
                        f"📉 {listing.title}\n{body}\n{listing.url}",
                    )
                    notification.sent_telegram = True
                except Exception:
                    logger.debug("price_drop telegram failed", exc_info=True)

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
            if user.telegram_connected and user.telegram_id:
                try:
                    await telegram_client.send_message(
                        user.telegram_id,
                        f"🔑 {listing.title}\n{body}\n{listing.url}",
                    )
                    notification.sent_telegram = True
                except Exception:
                    logger.debug("vin_found telegram failed", exc_info=True)

    if sent:
        await db.flush()
    return sent
