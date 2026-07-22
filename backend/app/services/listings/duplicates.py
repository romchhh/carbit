"""Крос-джерельне дедуплікування оголошень (лише за VIN)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing
from app.schemas.schemas import ListingOut, ListingSourceLink
from app.services.telegram_channels.mapper import fix_telegram_listing_url


_SOURCE_RANK = {
    "auto_ria": 0,
    "olx": 1,
    "telegram": 2,
}


def _source_rank(source: str) -> int:
    return _SOURCE_RANK.get((source or "").strip().lower(), 9)


def _normalize_vin(value: str | None) -> str:
    return (value or "").strip().upper()


def listings_look_same(a: ListingOut | Listing, b: ListingOut | Listing) -> bool:
    """Одне авто — лише якщо збігається повний 17-символьний VIN."""
    vin_a = _normalize_vin(getattr(a, "vin", None))
    vin_b = _normalize_vin(getattr(b, "vin", None))
    return bool(vin_a and vin_b and len(vin_a) == 17 and len(vin_b) == 17 and vin_a == vin_b)


async def find_duplicate_of(db: AsyncSession, data: ListingOut) -> Listing | None:
    """Шукає оголошення з тим самим VIN (інше джерело / repost)."""
    vin = _normalize_vin(data.vin)
    if not vin or len(vin) != 17:
        return None

    row = await db.scalar(
        select(Listing).where(
            func.upper(Listing.vin) == vin,
            Listing.id != data.id,
        ).limit(1)
    )
    return row


def _telegram_url_for(member: ListingOut) -> str:
    url = (member.url or "").strip()
    if (member.source or "").lower() != "telegram":
        return url
    return fix_telegram_listing_url(member.id, url, images=member.images)


def _pick_canonical(group: list[ListingOut], *, prefer_id: str | None = None) -> ListingOut:
    if prefer_id:
        for row in group:
            if row.id == prefer_id:
                return row
    return min(group, key=lambda row: (_source_rank(row.source), row.id or ""))


def _enrich_from_mirrors(canonical: ListingOut, members: list[ListingOut]) -> ListingOut:
    updates: dict = {}
    if not _normalize_vin(canonical.vin) or len(_normalize_vin(canonical.vin)) != 17:
        for m in members:
            vin = _normalize_vin(m.vin)
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


def mark_duplicates_in_pool(
    items: list[ListingOut],
    *,
    prefer_id: str | None = None,
) -> list[ListingOut]:
    """Згортає дублікати з однаковим VIN в одну картку з alternate_sources."""
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
        if len(group) == 1 and not _normalize_vin(group[0].vin):
            result.append(group[0])
            continue

        canonical = _pick_canonical(group, prefer_id=prefer_id)
        canonical = _enrich_from_mirrors(canonical, group)

        alternates: list[ListingSourceLink] = []
        seen_urls: set[str] = set()
        canon_url = _telegram_url_for(canonical) if canonical.source == "telegram" else (canonical.url or "")
        if canon_url:
            seen_urls.add(canon_url.rstrip("/").split("?", 1)[0])
        if canonical.source == "telegram" and canon_url:
            canonical = canonical.model_copy(update={"url": canon_url})

        for member in sorted(group, key=lambda row: (_source_rank(row.source), row.id)):
            if member.id == canonical.id:
                continue
            url = _telegram_url_for(member)
            if not url:
                continue
            url_key = url.rstrip("/").split("?", 1)[0]
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)
            alternates.append(
                ListingSourceLink(source=member.source, url=url, id=member.id)
            )

        is_new = any(bool(getattr(m, "is_new", None)) for m in group)

        result.append(
            canonical.model_copy(
                update={
                    "is_duplicate": False,
                    "duplicate_of": None,
                    "alternate_sources": alternates,
                    "is_new": True if is_new else canonical.is_new,
                }
            )
        )
    return result


def _pool_item_links_to_any(items: list[ListingOut], candidate: ListingOut) -> bool:
    return any(listings_look_same(candidate, item) for item in items)


async def collapse_listings_with_db_mirrors(
    db: AsyncSession,
    items: list[ListingOut],
    *,
    prefer_id: str | None = None,
) -> list[ListingOut]:
    """Підтягує дзеркала з БД лише за VIN / duplicate_of з тим самим VIN."""
    if not items:
        return []

    from sqlalchemy import or_

    from app.services.listings.serialize import listing_to_out

    orig_ids = {item.id for item in items}
    pool_by_id: dict[str, ListingOut] = {item.id: item for item in items}

    vins = sorted(
        {
            _normalize_vin(item.vin)
            for item in items
            if item.vin and len(_normalize_vin(item.vin)) == 17
        }
    )
    parent_ids = [item.duplicate_of for item in items if item.duplicate_of]

    clauses = []
    if orig_ids:
        clauses.append(Listing.duplicate_of.in_(list(orig_ids)))
    if parent_ids:
        clauses.append(Listing.id.in_(parent_ids))
    if vins:
        clauses.append(Listing.vin.in_(vins))

    if clauses:
        rows = (await db.scalars(select(Listing).where(or_(*clauses)).limit(800))).all()
        for row in rows:
            if row.id in pool_by_id:
                continue
            candidate = listing_to_out(row)
            if not _pool_item_links_to_any(items, candidate):
                continue
            pool_by_id[row.id] = candidate

    collapsed = mark_duplicates_in_pool(list(pool_by_id.values()), prefer_id=prefer_id)

    kept: list[ListingOut] = []
    for card in collapsed:
        member_ids = {card.id}
        for alt in card.alternate_sources or []:
            if alt.id:
                member_ids.add(alt.id)
        if member_ids & orig_ids:
            kept.append(card)
    return kept


async def listing_out_with_mirrors(db: AsyncSession, listing: Listing) -> ListingOut:
    from app.services.listings.serialize import listing_to_out

    out = listing_to_out(listing)
    collapsed = await collapse_listings_with_db_mirrors(db, [out], prefer_id=listing.id)
    return collapsed[0] if collapsed else out


async def clear_invalid_duplicate_links(db: AsyncSession) -> dict[str, int]:
    """Скидає is_duplicate/duplicate_of, якщо VIN не збігається (стара fuzzy-логіка)."""
    from app.services.listings.serialize import listing_to_out

    rows = (await db.scalars(select(Listing).where(Listing.duplicate_of.isnot(None)).limit(5000))).all()
    cleared = 0
    for row in rows:
        parent = await db.get(Listing, row.duplicate_of) if row.duplicate_of else None
        if parent is None:
            row.is_duplicate = False
            row.duplicate_of = None
            cleared += 1
            continue
        if not listings_look_same(listing_to_out(row), listing_to_out(parent)):
            row.is_duplicate = False
            row.duplicate_of = None
            cleared += 1
    return {"cleared": cleared, "scanned": len(rows)}
