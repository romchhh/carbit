"""Крос-джерельне дедуплікування оголошень (лише за VIN)."""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import norm_text
from app.models.models import Listing
from app.schemas.schemas import ListingOut, ListingSourceLink
from app.services.telegram_channels.mapper import fix_telegram_listing_url
from app.services.vin import is_valid_vin


_SOURCE_RANK = {
    "auto_ria": 0,
    "olx": 1,
    "telegram": 2,
}


def _source_rank(source: str) -> int:
    return _SOURCE_RANK.get((source or "").strip().lower(), 9)


def _normalize_vin(value: str | None) -> str:
    return (value or "").strip().upper()


def _normalize_model_key(model: str, *, brand: str = "") -> str:
    """Очистка назви моделі (OLX title split) — не для дедуплікації."""
    m = norm_text(model or "")
    m = re.sub(r"\b(19|20)\d{2}\b", "", m)
    m = re.sub(r"[^a-z0-9а-яёіїєґ\s-]", " ", m)
    brand_key = norm_text(brand or "")
    tokens = [
        t
        for t in m.split()
        if t and (not brand_key or t != brand_key)
    ]
    return tokens[0] if tokens else m.strip()


def listing_vin_for_dedup(item: ListingOut | Listing) -> str | None:
    """Валідний VIN для злиття дублів — інакше None (не dedup)."""
    vin = _normalize_vin(getattr(item, "vin", None))
    return vin if is_valid_vin(vin) else None


def _norm_telegram_channel(value: str | None) -> str:
    return (value or "").strip().lstrip("@").lower()


def _telegram_ids_from_listing_id(listing_id: str | None) -> tuple[str, int] | None:
    lid = (listing_id or "").strip()
    if not lid.startswith("telegram_"):
        return None
    body = lid.removeprefix("telegram_")
    channel_part, _, msg_part = body.rpartition("_")
    if not channel_part or not msg_part.isdigit():
        return None
    return _norm_telegram_channel(channel_part), int(msg_part)


def _telegram_url_dedupe_key(url: str | None) -> str | None:
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return None
    m = re.search(r"(?:https?://)?t\.me/([^/]+)/(\d+)", raw, re.IGNORECASE)
    if not m:
        return None
    slug = m.group(1).lower()
    if slug == "c":
        return None
    return f"tg:{_norm_telegram_channel(slug)}:{int(m.group(2))}"


def telegram_post_dedupe_key(item: ListingOut | Listing) -> str | None:
    """Один ключ на пост Telegram (канал + primary / album message id)."""
    source = getattr(item, "source", None)
    source_val = source.value if hasattr(source, "value") else str(source or "")
    if source_val.lower() != "telegram":
        return None

    sd = getattr(item, "source_data", None) or {}
    if not isinstance(sd, dict):
        sd = {}

    channel = _norm_telegram_channel(sd.get("channel"))
    if not channel:
        parsed = _telegram_ids_from_listing_id(getattr(item, "id", None))
        if parsed:
            channel = parsed[0]

    message_ids: list[int] = []
    for raw_ids in (sd.get("photo_message_ids"), sd.get("group_message_ids")):
        if not isinstance(raw_ids, list):
            continue
        for raw in raw_ids:
            try:
                message_ids.append(int(raw))
            except (TypeError, ValueError):
                continue
    if message_ids and channel:
        return f"tg:{channel}:{min(message_ids)}"

    if channel and sd.get("message_id") is not None:
        try:
            return f"tg:{channel}:{int(sd['message_id'])}"
        except (TypeError, ValueError):
            pass

    parsed = _telegram_ids_from_listing_id(getattr(item, "id", None))
    if parsed:
        return f"tg:{parsed[0]}:{parsed[1]}"

    url_key = _telegram_url_dedupe_key(getattr(item, "url", None))
    if url_key:
        return url_key
    return None


def _telegram_listing_rank(row: ListingOut) -> tuple[int, int, int]:
    return (
        len(row.images or []),
        len((row.description or "").strip()),
        len((row.title or "").strip()),
    )


def _prefer_telegram_listing(a: ListingOut, b: ListingOut) -> ListingOut:
    """Яку картку лишити при дублі одного TG-поста."""
    return a if _telegram_listing_rank(a) >= _telegram_listing_rank(b) else b


def dedupe_telegram_posts_in_pool(items: list[ListingOut]) -> list[ListingOut]:
    """Прибирає повтори одного Telegram-поста (різні listing.id / re-ingest)."""
    if not items:
        return []

    best: dict[str, ListingOut] = {}
    for item in items:
        key = telegram_post_dedupe_key(item)
        if not key:
            continue
        if key not in best:
            best[key] = item
        else:
            best[key] = _prefer_telegram_listing(best[key], item)

    out: list[ListingOut] = []
    seen_ids: set[str] = set()
    emitted_tg: set[str] = set()

    for item in items:
        key = telegram_post_dedupe_key(item)
        if key:
            if key in emitted_tg:
                continue
            emitted_tg.add(key)
            row = best[key]
            if row.id in seen_ids:
                continue
            seen_ids.add(row.id)
            out.append(row)
            continue
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        out.append(item)
    return out


def listings_look_same(a: ListingOut | Listing, b: ListingOut | Listing) -> bool:
    """Одне авто — лише при збігу валідного 17-символьного VIN."""
    vin_a = listing_vin_for_dedup(a)
    vin_b = listing_vin_for_dedup(b)
    return bool(vin_a and vin_b and vin_a == vin_b)


async def find_duplicate_of(db: AsyncSession, data: ListingOut) -> Listing | None:
    """Шукає oголошення з тим самим VIN (інше джерело / repost)."""
    vin = listing_vin_for_dedup(data)
    if not vin:
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
    if not listing_vin_for_dedup(canonical):
        for m in members:
            vin = listing_vin_for_dedup(m)
            if vin:
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
        if len(group) == 1 and not listing_vin_for_dedup(group[0]):
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
            v
            for item in items
            if (v := listing_vin_for_dedup(item))
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
