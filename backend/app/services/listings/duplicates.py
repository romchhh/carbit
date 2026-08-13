"""Крос-джерельне дедуплікування оголошень (VIN + Telegram reposts)."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import norm_text
from app.models.models import Listing
from app.schemas.schemas import ListingOut, ListingSourceLink
from app.services.telegram_channels.mapper import fix_telegram_listing_url
from app.services.vin import is_valid_vin

# Прибираємо телефони / ціни з тексту, щоб репост із новою ціною схлопувався.
_TG_TEXT_NOISE_RE = re.compile(
    r"(?:"
    r"\b(?:\+?38)?0\d{8,10}\b"
    r"|\b\d{1,3}(?:[ \u00a0]\d{3})+\s*(?:грн|\$|usd|eur|у\.?\s?е\.?)?\b"
    r"|\b\d{3,6}\s*(?:грн|\$|usd|eur)\b"
    r"|https?://\S+"
    r"|t\.me/\S+"
    r")",
    re.IGNORECASE,
)


_SOURCE_RANK = {
    "auto_ria": 0,
    "olx": 1,
    "imperiya": 2,
    "telegram": 3,
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
    if is_valid_vin(vin):
        return vin
    return None


def enrich_listing_vin_for_dedup(item: ListingOut) -> ListingOut:
    """Доповнює VIN з title/description перед крос-джерельним dedup."""
    if listing_vin_for_dedup(item):
        return item
    from app.services.vin import extract_vin

    vin = extract_vin(
        getattr(item, "description", None),
        getattr(item, "title", None),
        getattr(item, "brand", None),
        getattr(item, "model", None),
    )
    if vin:
        return item.model_copy(update={"vin": vin})
    return item


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


def _telegram_price_bucket(price: int, *, step: int | None = None) -> int:
    """Груба ціна: step=500 (~дрібні правки), step=2000 (короткі дублі в каналі)."""
    if price <= 0:
        return 0
    if step is None:
        step = 500 if price < 50_000 else 1000
    return int(round(price / step) * step)


def _telegram_body_for_fingerprint(item: ListingOut | Listing) -> str:
    title = (getattr(item, "title", None) or "").strip()
    desc = (getattr(item, "description", None) or "").strip()
    # Якщо description починається з title — не дублюємо.
    if desc and title and norm_text(desc).startswith(norm_text(title)[:40]):
        raw = desc
    else:
        raw = f"{title}\n{desc}".strip()
    cleaned = _TG_TEXT_NOISE_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", norm_text(cleaned)).strip()


def telegram_text_fingerprint(item: ListingOut | Listing) -> str | None:
    """Один і той самий текст оголошення (репост / правка ціни), крос-канально."""
    source = getattr(item, "source", None)
    source_val = source.value if hasattr(source, "value") else str(source or "")
    if source_val.lower() != "telegram":
        return None

    body = _telegram_body_for_fingerprint(item)
    if len(body) < 48:
        return None
    digest = hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
    year = int(getattr(item, "year", 0) or 0)
    year_part = str(year) if year >= 1990 else "0"
    return f"tgtxt:{digest}:{year_part}"


def telegram_channel_title_fingerprint(item: ListingOut | Listing) -> str | None:
    """Той самий короткий пост у каналі (різні message_id / близька ціна)."""
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
    if not channel:
        return None

    title = norm_text(getattr(item, "title", None) or "")
    if len(title) < 12:
        body = _telegram_body_for_fingerprint(item)
        title = body[:72] if len(body) >= 12 else ""
    if len(title) < 12:
        return None

    year = int(getattr(item, "year", 0) or 0)
    if year < 1990:
        return None
    try:
        price = int(round(float(getattr(item, "price", 0) or 0)))
    except (TypeError, ValueError):
        price = 0
    if price <= 0:
        return None
    # step=2000: 16k≈17k, 18k≈18.5k; 22k≠29k лишаються різними
    return f"tgch:{channel}:{title[:80]}:{year}:{_telegram_price_bucket(price, step=2000)}"


def telegram_content_fingerprint(item: ListingOut | Listing) -> str | None:
    """Ключ репосту одного авто в різних TG-каналах (бренд+модель+рік+ціна±bucket)."""
    source = getattr(item, "source", None)
    source_val = source.value if hasattr(source, "value") else str(source or "")
    if source_val.lower() != "telegram":
        return None

    try:
        price = int(round(float(getattr(item, "price", 0) or 0)))
    except (TypeError, ValueError):
        price = 0
    if price <= 0:
        return None

    price_bucket = _telegram_price_bucket(price)
    currency = str(getattr(item, "currency", "") or "").strip().upper() or "USD"
    year = int(getattr(item, "year", 0) or 0)
    brand = norm_text(getattr(item, "brand", None) or "")
    model = norm_text(getattr(item, "model", None) or "")
    try:
        mileage = int(getattr(item, "mileage", 0) or 0)
    except (TypeError, ValueError):
        mileage = 0
    mile_bucket = (mileage // 5000) * 5000 if mileage > 0 else 0

    if brand and year >= 1990:
        return f"tgfp:{brand}:{model}:{year}:{price_bucket}:{currency}:{mile_bucket}"

    title = norm_text(getattr(item, "title", None) or "")
    # Без марки — лише якщо заголовок досить довгий і є рік/ціна.
    if len(title) >= 24 and year >= 1990:
        return f"tgfp:t:{title[:72]}:{year}:{price_bucket}:{currency}:{mile_bucket}"
    return None


def _telegram_listing_rank(row: ListingOut) -> tuple:
    published = getattr(row, "published_at", None) or getattr(row, "found_at", None)
    # newer → більший ts для порівняння
    ts = published.timestamp() if published is not None else 0.0
    # З репостів одного авто показуємо картку з фото і найсвіжішу: різниця
    # в пару символів заголовка не варта того, щоб показати місячний пост.
    return (
        1 if row.images else 0,
        ts,
        len(row.images or []),
        len((row.description or "").strip()),
        len((row.title or "").strip()),
    )


def _prefer_telegram_listing(a: ListingOut, b: ListingOut) -> ListingOut:
    """Яку картку лишити при дублі одного TG-поста."""
    return a if _telegram_listing_rank(a) >= _telegram_listing_rank(b) else b


def _collapse_by_key(
    items: list[ListingOut],
    key_fn,
) -> list[ListingOut]:
    best: dict[str, ListingOut] = {}

    for item in items:
        key = key_fn(item)
        if not key:
            continue
        if key not in best:
            best[key] = item
        else:
            best[key] = _prefer_telegram_listing(best[key], item)

    out: list[ListingOut] = []
    seen_ids: set[str] = set()
    emitted_keys: set[str] = set()

    for item in items:
        key = key_fn(item)
        if key:
            if key in emitted_keys:
                continue
            emitted_keys.add(key)
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


def dedupe_telegram_posts_in_pool(items: list[ListingOut]) -> list[ListingOut]:
    """Прибирає повтори одного Telegram-поста та крос-канальні репости."""
    if not items:
        return []
    # 1) той самий пост (канал+message_id / album)
    by_post = _collapse_by_key(items, telegram_post_dedupe_key)
    # 2) той самий текст (репост / правка ціни), крос-канально
    by_text = _collapse_by_key(by_post, telegram_text_fingerprint)
    # 3) короткий дубль у тому ж каналі (однаковий title+рік)
    by_channel = _collapse_by_key(by_text, telegram_channel_title_fingerprint)
    # 4) бренд+модель+рік+ціна±bucket (класичний fingerprint)
    return _collapse_by_key(by_channel, telegram_content_fingerprint)


def listings_look_same(a: ListingOut | Listing, b: ListingOut | Listing) -> bool:
    """Одне авто — лише при збігу валідного 17-символьного VIN."""
    vin_a = listing_vin_for_dedup(a)
    vin_b = listing_vin_for_dedup(b)
    return bool(vin_a and vin_b and vin_a == vin_b)


async def find_duplicate_of(db: AsyncSession, data: ListingOut) -> Listing | None:
    """Шукає oголошення з тим самим VIN (інше джерело / repost)."""
    vin = listing_vin_for_dedup(data)
    if not vin:
        enriched = enrich_listing_vin_for_dedup(data)
        vin = listing_vin_for_dedup(enriched)
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
    items = [enrich_listing_vin_for_dedup(item) for item in items]
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
            if member.id != canonical.id:
                url = _telegram_url_for(member)
                if url:
                    url_key = url.rstrip("/").split("?", 1)[0]
                    if url_key not in seen_urls:
                        seen_urls.add(url_key)
                        alternates.append(
                            ListingSourceLink(source=member.source, url=url, id=member.id)
                        )
            # Дзеркала, знайдені попереднім склеюванням, треба зберегти: інакше
            # повторний прохід (пул → collapse_listings_with_db_mirrors) їх стирає.
            for link in member.alternate_sources or []:
                if not link.url:
                    continue
                url_key = link.url.rstrip("/").split("?", 1)[0]
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                alternates.append(link)

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


def _candidate_belongs_in_mirror_pool(
    candidate: ListingOut,
    pool_by_id: dict[str, ListingOut],
    orig_ids: set[str],
) -> bool:
    """Чи додавати запис з БД до пулу дзеркал (VIN, duplicate_of, reverse link)."""
    if candidate.id in orig_ids:
        return True
    dup_of = (candidate.duplicate_of or "").strip()
    if dup_of and dup_of in orig_ids:
        return True
    for item in pool_by_id.values():
        if (item.duplicate_of or "").strip() == candidate.id:
            return True
        if listings_look_same(candidate, item):
            return True
    return False


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

    items = [enrich_listing_vin_for_dedup(item) for item in items]
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
            candidate = enrich_listing_vin_for_dedup(listing_to_out(row))
            if not _candidate_belongs_in_mirror_pool(candidate, pool_by_id, orig_ids):
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
    from app.services.telegram_channels.lazy_photos import sync_telegram_photos_from_disk

    await sync_telegram_photos_from_disk(db, listing)
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
