from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing, Source
from app.schemas.schemas import ListingOut


def _parse_source(value: str) -> Source:
    try:
        return Source(value)
    except ValueError:
        return Source.auto_ria


def _external_id(listing_id: str) -> str:
    if listing_id.startswith("auto_ria_"):
        return listing_id.removeprefix("auto_ria_")
    return listing_id


async def upsert_listing(db: AsyncSession, data: ListingOut) -> Listing:
    listing = await db.get(Listing, data.id)
    payload = {
        "external_id": _external_id(data.id),
        "source": _parse_source(data.source),
        "title": data.title,
        "brand": data.brand,
        "model": data.model,
        "year": data.year,
        "price": data.price,
        "currency": data.currency or "UAH",
        "mileage": data.mileage,
        "fuel": data.fuel or "",
        "transmission": data.transmission or "",
        "region": data.region or "",
        "description": data.description,
        "images": data.images or [],
        "url": data.url,
        "seller_type": data.seller_type or "private",
        "price_history": data.price_history or [],
        "is_duplicate": data.is_duplicate,
        "published_at": data.published_at,
        "found_at": data.found_at or datetime.now(UTC),
    }

    if listing:
        for key, value in payload.items():
            setattr(listing, key, value)
        return listing

    listing = Listing(id=data.id, **payload)
    db.add(listing)
    await db.flush()
    return listing
