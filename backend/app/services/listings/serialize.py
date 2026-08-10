from __future__ import annotations

from app.models.models import Listing
from app.schemas.schemas import ListingOut
from app.services.telegram_channels.mapper import fix_telegram_listing_url


def listing_to_out(listing: Listing) -> ListingOut:
    from app.core.timezone import as_kyiv, now_kyiv
    from app.services.currency import normalize_currency
    from app.services.vin import extract_vin

    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    images = list(listing.images or [])
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

    volume = extract_listing_engine_volume(out)
    if volume is not None:
        return out.model_copy(update={"engine_volume_l": volume})
    return out
