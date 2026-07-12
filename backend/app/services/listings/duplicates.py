"""Крос-джерельне дедуплікування оголошень."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import norm_text
from app.models.models import Listing
from app.schemas.schemas import ListingOut


def _mileage_close(a: int, b: int) -> bool:
    if a <= 0 or b <= 0:
        return False
    lo, hi = min(a, b), max(a, b)
    if hi <= 0:
        return False
    return (hi - lo) / hi <= 0.08 or abs(hi - lo) <= 3000


def listings_look_same(a: ListingOut | Listing, b: ListingOut | Listing) -> bool:
    vin_a = (getattr(a, "vin", None) or "").strip().upper()
    vin_b = (getattr(b, "vin", None) or "").strip().upper()
    if vin_a and vin_b and len(vin_a) == 17 and vin_a == vin_b:
        return True

    brand_a = norm_text(getattr(a, "brand", "") or "")
    brand_b = norm_text(getattr(b, "brand", "") or "")
    model_a = norm_text(getattr(a, "model", "") or "")
    model_b = norm_text(getattr(b, "model", "") or "")
    year_a = int(getattr(a, "year", 0) or 0)
    year_b = int(getattr(b, "year", 0) or 0)
    if not brand_a or not brand_b or brand_a != brand_b:
        return False
    if not model_a or not model_b or model_a != model_b:
        return False
    if not year_a or year_a != year_b:
        return False
    return _mileage_close(int(getattr(a, "mileage", 0) or 0), int(getattr(b, "mileage", 0) or 0))


async def find_duplicate_of(db: AsyncSession, data: ListingOut) -> Listing | None:
    """Шукає вже збережене оголошення з іншого джерела, схоже на data."""
    if data.vin and len(data.vin) == 17:
        row = await db.scalar(
            select(Listing).where(
                Listing.vin == data.vin.upper(),
                Listing.id != data.id,
            ).limit(1)
        )
        if row:
            return row

    if not data.brand or not data.model or not data.year:
        return None

    candidates = (
        await db.scalars(
            select(Listing)
            .where(
                Listing.brand == data.brand,
                Listing.model == data.model,
                Listing.year == data.year,
                Listing.id != data.id,
                Listing.is_duplicate.is_(False),
            )
            .limit(40)
        )
    ).all()

    for candidate in candidates:
        if listings_look_same(data, candidate):
            return candidate
    return None


def mark_duplicates_in_pool(items: list[ListingOut]) -> list[ListingOut]:
    """Позначає дублікати в межах однієї видачі (перший — канонічний)."""
    result: list[ListingOut] = []
    canonical: list[ListingOut] = []
    for item in items:
        match = next((c for c in canonical if listings_look_same(item, c)), None)
        if match is None:
            canonical.append(item)
            result.append(item.model_copy(update={"is_duplicate": False, "duplicate_of": None}))
        else:
            result.append(
                item.model_copy(update={"is_duplicate": True, "duplicate_of": match.id})
            )
    return result
