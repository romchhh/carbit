from __future__ import annotations

from app.core.timezone import now_kyiv

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Source
from app.schemas.schemas import ListingOut
from app.services.listings.duplicates import find_duplicate_of, listing_vin_for_dedup
from app.services.vin import extract_vin, is_valid_vin


def _parse_source(value: str) -> Source:
    try:
        return Source(value)
    except ValueError:
        return Source.auto_ria


def _external_id(listing_id: str) -> str:
    for prefix in ("auto_ria_", "olx_", "telegram_", "imperiya_"):
        if listing_id.startswith(prefix):
            return listing_id.removeprefix(prefix)
    return listing_id


def _append_price_history(listing: Listing, new_price: int, currency: str) -> list:
    history = list(listing.price_history or [])
    if listing.price and int(listing.price) != int(new_price):
        history.append(
            {
                "price": int(listing.price),
                "currency": listing.currency or currency,
                "at": (listing.found_at or now_kyiv()).isoformat(),
            }
        )
    return history[-30:]


async def upsert_listing(db: AsyncSession, data: ListingOut) -> Listing:
    listing = await db.get(Listing, data.id)
    raw = (data.vin or extract_vin(data.description, data.title) or "").strip().upper()
    vin = raw if is_valid_vin(raw) else None

    duplicate = await find_duplicate_of(db, data.model_copy(update={"vin": vin}))
    if duplicate:
        is_duplicate = True
        duplicate_of = duplicate.id
    else:
        is_duplicate = False
        duplicate_of = None

    price_changed = False
    vin_appeared = False
    old_price = None
    old_currency = None

    if listing:
        old_price = int(listing.price or 0)
        old_currency = listing.currency
        if old_price and old_price != int(data.price):
            price_changed = True
        if vin and not (listing.vin or "").strip():
            vin_appeared = True
        history = _append_price_history(listing, data.price, data.currency or "USD")
        keep_found_at = listing.found_at or data.found_at or now_kyiv()
    else:
        history = list(data.price_history or [])
        keep_found_at = data.found_at or now_kyiv()

    payload = {
        "external_id": _external_id(data.id),
        "source": _parse_source(data.source),
        "title": data.title,
        "brand": data.brand,
        "model": data.model,
        "year": data.year,
        "price": data.price,
        "currency": data.currency or "USD",
        "mileage": data.mileage,
        "fuel": data.fuel or "",
        "transmission": data.transmission or "",
        "region": data.region or "",
        "description": data.description,
        "images": data.images or [],
        "url": data.url,
        "seller_name": data.seller_name,
        "seller_phone": data.seller_phone,
        "seller_telegram": data.seller_telegram,
        "seller_url": data.seller_url,
        "seller_type": data.seller_type or "private",
        "price_history": history,
        "vin": vin,
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "published_at": data.published_at,
        "refreshed_at": data.refreshed_at,
        "found_at": keep_found_at,
    }

    if listing:
        # Не затираємо вже завантажені lazy-фото порожнім масивом з повторного ingest
        if listing.images and not (data.images or []):
            payload["images"] = listing.images
        for key, value in payload.items():
            setattr(listing, key, value)
    else:
        listing = Listing(id=data.id, **payload)
        db.add(listing)

    await db.flush()

    # Алерти «ціна впала» / «з’явився VIN» для вже прив’язаних пошуків.
    # Порівнюємо в грн: сирі числа в різних валютах (UAH↔USD) давали хибні «зниження».
    if listing and (price_changed or vin_appeared):
        from app.services.currency import listing_price_uah
        from app.services.notifications.listing_events import notify_listing_events

        price_dropped = False
        if price_changed and old_price:
            old_uah = listing_price_uah(old_price, old_currency)
            new_uah = listing_price_uah(data.price, data.currency or listing.currency)
            # Реальне падіння в еквіваленті грн (не шум від зміни валюти/курсу)
            price_dropped = old_uah > 0 and new_uah > 0 and new_uah < old_uah

        await notify_listing_events(
            db,
            listing,
            price_dropped=price_dropped,
            old_price=old_price,
            old_currency=old_currency,
            vin_appeared=vin_appeared,
        )

    return listing


async def upsert_listing_with_mirrors(db: AsyncSession, data: ListingOut) -> Listing:
    """Upsert канонічного оголошення + дзеркал з `alternate_sources` (лише при VIN)."""
    listing = await upsert_listing(db, data)
    canonical_vin = listing_vin_for_dedup(listing)
    for alt in data.alternate_sources or []:
        if not alt.url or not alt.source:
            continue
        mirror_id = (alt.id or "").strip()
        if not mirror_id or mirror_id == listing.id:
            continue
        mirror_updates: dict = {
            "id": mirror_id,
            "source": alt.source,
            "url": alt.url,
            "images": [],
            "source_data": None,
            "price_history": [],
            "alternate_sources": [],
        }
        if canonical_vin:
            mirror_updates["is_duplicate"] = True
            mirror_updates["duplicate_of"] = listing.id
            mirror_updates["vin"] = canonical_vin
        mirror = data.model_copy(update=mirror_updates)
        await upsert_listing(db, mirror)
    return listing
