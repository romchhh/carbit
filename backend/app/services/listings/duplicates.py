"""Крос-джерельне дедуплікування оголошень."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import norm_text
from app.models.models import Listing
from app.schemas.schemas import ListingOut, ListingSourceLink


_SOURCE_RANK = {
    "auto_ria": 0,
    "olx": 1,
    "telegram": 2,
}


def _source_rank(source: str) -> int:
    return _SOURCE_RANK.get((source or "").strip().lower(), 9)


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


def _pick_group_members(group: list[ListingOut]) -> list[ListingOut]:
    """Один запис на джерело (найсвіжіший)."""
    by_source: dict[str, ListingOut] = {}
    for item in group:
        key = (item.source or "").strip().lower() or "unknown"
        prev = by_source.get(key)
        if prev is None or (item.published_at or item.found_at) > (prev.published_at or prev.found_at):
            by_source[key] = item
    return list(by_source.values())


def _enrich_from_mirrors(canonical: ListingOut, members: list[ListingOut]) -> ListingOut:
    """Доповнює AUTO.RIA-картку VIN/фото з дзеркал, якщо бракує."""
    updates: dict = {}
    if not (canonical.vin or "").strip():
        for m in members:
            vin = (m.vin or "").strip().upper()
            if len(vin) == 17:
                updates["vin"] = vin
                break
    if not canonical.images:
        for m in members:
            if m.images:
                updates["images"] = list(m.images)
                break
    if not updates:
        return canonical
    return canonical.model_copy(update=updates)


def mark_duplicates_in_pool(items: list[ListingOut]) -> list[ListingOut]:
    """Згортає крос-джерельні дублікати в одну картку.

    Канонічне оголошення — пріоритетно AUTO.RIA; у `alternate_sources` —
    посилання на інші джерела з іконками на UI.
    """
    groups: list[list[ListingOut]] = []
    for item in items:
        placed = False
        for group in groups:
            if any(listings_look_same(item, existing) for existing in group):
                group.append(item)
                placed = True
                break
        if not placed:
            groups.append([item])

    result: list[ListingOut] = []
    for group in groups:
        members = _pick_group_members(group)
        canonical = min(members, key=lambda row: _source_rank(row.source))
        canonical = _enrich_from_mirrors(canonical, members)

        alternates: list[ListingSourceLink] = []
        seen_sources = {canonical.source}
        for member in sorted(members, key=lambda row: _source_rank(row.source)):
            if member.id == canonical.id:
                continue
            if member.source in seen_sources:
                continue
            seen_sources.add(member.source)
            if not member.url:
                continue
            alternates.append(
                ListingSourceLink(source=member.source, url=member.url, id=member.id)
            )

        result.append(
            canonical.model_copy(
                update={
                    "is_duplicate": False,
                    "duplicate_of": None,
                    "alternate_sources": alternates,
                }
            )
        )
    return result
