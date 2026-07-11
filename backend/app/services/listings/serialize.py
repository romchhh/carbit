from __future__ import annotations

from app.models.models import Listing
from app.schemas.schemas import ListingOut
from app.services.telegram_channels.mapper import fix_telegram_listing_url


def listing_to_out(listing: Listing) -> ListingOut:
    from app.core.timezone import as_kyiv, now_kyiv

    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    url = listing.url
    if source == "telegram":
        url = fix_telegram_listing_url(listing.id, url, images=listing.images)
    published_at = as_kyiv(listing.published_at) if listing.published_at else now_kyiv()
    found_at = as_kyiv(listing.found_at) if listing.found_at else now_kyiv()
    return ListingOut(
        id=listing.id,
        source=source,
        title=listing.title or "",
        brand=listing.brand or "",
        model=listing.model or "",
        year=int(listing.year or 0),
        price=int(listing.price or 0),
        currency=listing.currency or "грн",
        mileage=int(listing.mileage or 0),
        fuel=listing.fuel or "",
        transmission=listing.transmission or "",
        region=listing.region or "",
        description=listing.description,
        images=listing.images or [],
        url=url or "",
        seller_type=listing.seller_type or "private",
        vin=None,
        vin_checked=None,
        vin_check_url=None,
        source_data=None,
        price_history=listing.price_history or [],
        is_duplicate=bool(listing.is_duplicate),
        published_at=published_at,
        found_at=found_at,
    )
