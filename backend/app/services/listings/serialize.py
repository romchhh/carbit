from __future__ import annotations

from app.models.models import Listing
from app.schemas.schemas import ListingOut
from app.services.telegram_channels.mapper import fix_telegram_listing_url


def listing_to_out(listing: Listing) -> ListingOut:
    from app.core.timezone import as_kyiv, now_kyiv
    from app.services.currency import normalize_currency
    from app.services.telegram.media_urls import filter_existing_image_urls
    from app.services.vin import extract_vin

    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    # БД може тримати URL після purge media/ — показуємо лише існуючі файли
    images = filter_existing_image_urls(listing.images)
    if source == "telegram" and not images:
        from app.services.telegram_channels.lazy_photos import load_existing_telegram_photo_urls

        images = load_existing_telegram_photo_urls(listing.id, limit=1)

    url = listing.url
    if source == "telegram":
        url = fix_telegram_listing_url(listing.id, url, images=images)
    published_at = as_kyiv(listing.published_at) if listing.published_at else now_kyiv()
    found_at = as_kyiv(listing.found_at) if listing.found_at else now_kyiv()
    # Старі записи в БД — грн; нові — оригінальна валюта з джерела.
    raw_currency = listing.currency or "UAH"
    currency = normalize_currency(raw_currency)
    if currency not in {"UAH", "USD", "EUR"}:
        currency = "UAH"

    vin = extract_vin(listing.description, listing.title) or getattr(listing, "vin", None)

    source_data = None
    if source == "telegram" and not images:
        source_data = {"photos_pending": True}

    out = ListingOut(
        id=listing.id,
        source=source,
        title=listing.title or "",
        brand=listing.brand or "",
        model=listing.model or "",
        year=int(listing.year or 0),
        price=int(listing.price or 0),
        currency=currency,
        mileage=int(listing.mileage or 0),
        fuel=listing.fuel or "",
        transmission=listing.transmission or "",
        region=listing.region or "",
        description=listing.description,
        images=images,
        url=url or "",
        seller_type=listing.seller_type or "private",
        seller_name=getattr(listing, "seller_name", None),
        seller_phone=getattr(listing, "seller_phone", None),
        seller_telegram=getattr(listing, "seller_telegram", None),
        seller_url=getattr(listing, "seller_url", None),
        vin=(vin or None),
        vin_checked=None,
        vin_check_url=None,
        source_data=source_data,
        price_history=listing.price_history or [],
        is_duplicate=bool(listing.is_duplicate),
        duplicate_of=getattr(listing, "duplicate_of", None),
        published_at=published_at,
        refreshed_at=as_kyiv(listing.refreshed_at) if getattr(listing, "refreshed_at", None) else None,
        found_at=found_at,
    )
    from app.services.listings.engine_volume import extract_listing_engine_volume

    from app.services.listings.seller_contact import enrich_listing_seller_contact

    out = enrich_listing_seller_contact(out)
    volume = extract_listing_engine_volume(out)
    if volume is not None:
        out = out.model_copy(update={"engine_volume_l": volume})

    from app.services.listings.price_drop import extract_recent_price_drop

    drop = extract_recent_price_drop(listing)
    if drop:
        out = out.model_copy(
            update={
                "previous_price": drop.previous_price,
                "price_drop_percent": drop.drop_percent,
                "price_dropped_at": drop.dropped_at,
            }
        )
    return out
