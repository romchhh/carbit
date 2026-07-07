from __future__ import annotations

from app.models.models import Listing
from app.schemas.schemas import ListingOut


def listing_to_out(listing: Listing) -> ListingOut:
    source = listing.source.value if hasattr(listing.source, "value") else str(listing.source)
    return ListingOut(
        id=listing.id,
        source=source,
        title=listing.title,
        brand=listing.brand,
        model=listing.model,
        year=listing.year,
        price=listing.price,
        currency=listing.currency,
        mileage=listing.mileage,
        fuel=listing.fuel,
        transmission=listing.transmission,
        region=listing.region,
        description=listing.description,
        images=listing.images or [],
        url=listing.url,
        seller_type=listing.seller_type,
        vin=None,
        vin_checked=None,
        vin_check_url=None,
        source_data=None,
        price_history=listing.price_history or [],
        is_duplicate=listing.is_duplicate,
        published_at=listing.published_at,
        found_at=listing.found_at,
    )
