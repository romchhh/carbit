"""KV-кеш повного пулу live-пошуку — пагінація без повторних запитів до джерел.

Slot-based pool format (Redis):
  {
    "slots": [
      {"s": "r", "i": "12345"},          # AUTO.RIA вживані — тільки ID, гідратується через /auto/info
      {"s": "n", "i": "1928969"},         # AUTO.RIA нові   — тільки ID, гідратується через /auto/new/auto
      {"s": "o", "d": {...listing}},      # OLX      — повний об'єкт
      {"s": "i", "d": {...listing}},      # Імперія  — повний об'єкт
      {"s": "u", "d": {...listing}},      # uDrive   — повний об'єкт
      {"s": "c", "d": {...listing}},      # Car Market — повний об'єкт
      {"s": "e", "d": {...listing}},      # REONO — повний об'єкт
      {"s": "t", "d": {...listing}},      # Telegram — повний об'єкт
      ...
    ],
    "total": 310,           # кількість слотів (для пагінації)
    "market_total": 292,    # реальна кількість оголошень в AUTO.RIA API
    "sources": [...],
    "partial": false
  }

Кожне AUTO.RIA-оголошення гідратується лише при відображенні сторінки.
Кеш окремих оголошень: ar-info:{id} (вживані) і ar-new-info:{id} (нові), по 10 хв.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, TypeGuard

from app.core.redis import get_redis
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters, SourceStatusOut
from app.services.parser.filter_groups import filters_group_key

logger = logging.getLogger(__name__)

LIVE_POOL_PREFIX = "live-pool:"
LIVE_POOL_TTL_SECONDS = 600  # 10 хвилин — повторний пошук без нових AR-запитів
# Максимальна кількість слотів у пулі (AUTO.RIA IDs + OLX/Telegram items)
LIVE_POOL_SIZE = 500

# Кеш окремих AUTO.RIA-оголошень (щоб не гідратувати одне й те саме двічі)
_AR_INFO_PREFIX = "ar-info:"
_AR_NEW_INFO_PREFIX = "ar-new-info:"
_AR_INFO_TTL_SECONDS = 1800  # 30 хвилин — /auto/info платний, тримаємо довше


def live_pool_cache_key(filters: SearchFilters, sort_by: str) -> str:
    payload = f"{filters_group_key(filters)}|{sort_by}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"{LIVE_POOL_PREFIX}{digest}"


async def get_live_pool(filters: SearchFilters, sort_by: str) -> dict[str, Any] | None:
    try:
        redis = await get_redis()
        raw = await redis.get(live_pool_cache_key(filters, sort_by))
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        # Підтримка обох форматів: новий (slots) і старий (items)
        if not isinstance(data.get("slots"), list) and not isinstance(data.get("items"), list):
            return None
        return data
    except Exception:
        logger.exception("Live pool cache read failed")
        return None


async def set_live_pool(
    filters: SearchFilters,
    sort_by: str,
    *,
    slots: list[dict],
    total: int,
    market_total: int | None = None,
    sources: list[SourceStatusOut] | list[dict] | None = None,
    partial: bool = False,
    model_post_filter: bool = False,
    ttl_seconds: int = LIVE_POOL_TTL_SECONDS,
) -> None:
    try:
        redis = await get_redis()
        payload = {
            "slots": slots,
            "sources": [
                s.model_dump() if isinstance(s, SourceStatusOut) else s
                for s in (sources or [])
            ],
            "partial": partial,
            "total": total,
            "market_total": market_total,
            "model_post_filter": model_post_filter,
        }
        await redis.setex(
            live_pool_cache_key(filters, sort_by),
            ttl_seconds,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        logger.exception("Live pool cache write failed")


# ---------------------------------------------------------------------------
# AUTO.RIA on-demand hydration
# ---------------------------------------------------------------------------


async def _batch_hydrate_auto_ria(ids: list[str]) -> dict[str, ListingOut]:
    """Гідратує AUTO.RIA оголошення за ID. Використовує окремий Redis-кеш на 10 хвилин."""
    if not ids:
        return {}

    from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
    from app.services.auto_ria.mapper import info_to_listing
    from app.services.auto_ria.page_badges import attach_page_badges_to_info

    result: dict[str, ListingOut] = {}
    to_fetch: list[str] = []

    # Читаємо весь батч за один MGET замість N окремих GET
    try:
        redis = await get_redis()
        keys = [f"{_AR_INFO_PREFIX}{aid}" for aid in ids]
        raws = await redis.mget(*keys)
        for aid, raw in zip(ids, raws):
            if raw:
                try:
                    result[aid] = ListingOut.model_validate(json.loads(raw))
                except Exception:
                    to_fetch.append(aid)
            else:
                to_fetch.append(aid)
    except Exception:
        logger.exception("AR info cache read failed")
        to_fetch = list(ids)

    if not to_fetch:
        return result

    # Гідратуємо некешовані
    client = AutoRiaClient()
    sem = asyncio.Semaphore(10)

    async def fetch_one(aid: str) -> tuple[str, ListingOut | None]:
        async with sem:
            try:
                info = await client.get_info(aid)
                info = await attach_page_badges_to_info(info)
                listing = info_to_listing(info, fotos=None)
                return aid, listing
            except (AutoRiaError, Exception):
                # Вживані ID не пробуємо /auto/new/auto — це другий платний запит на промах.
                return aid, None

    fetched = await asyncio.gather(*(fetch_one(aid) for aid in to_fetch))

    # Зберігаємо в кеш через pipeline — один round-trip замість N
    for aid, listing in fetched:
        if listing:
            result[aid] = listing
    try:
        redis = await get_redis()
        pipe = redis.pipeline(transaction=False)
        for aid, listing in fetched:
            if listing:
                pipe.setex(f"{_AR_INFO_PREFIX}{aid}", _AR_INFO_TTL_SECONDS, listing.model_dump_json())
        await pipe.execute()
    except Exception:
        pass

    return result


async def hydrate_tagged_auto_ria_ids(
    ids: list[str],
    *,
    limit: int | None = None,
) -> list[ListingOut]:
    """Гідратує tagged IDs (`123` вживані, `n:456` нові) зі спільним Redis-кешем."""
    tagged = list(ids[:limit] if limit is not None else ids)
    if not tagged:
        return []
    used_ids = [aid for aid in tagged if not aid.startswith("n:")]
    new_ids = [aid[2:] for aid in tagged if aid.startswith("n:")]
    hydrated_used, hydrated_new = await asyncio.gather(
        _batch_hydrate_auto_ria(used_ids),
        _batch_hydrate_new_auto_ria(new_ids),
    )
    items: list[ListingOut] = []
    seen: set[str] = set()
    for aid in tagged:
        listing = (
            hydrated_new.get(aid[2:]) if aid.startswith("n:") else hydrated_used.get(aid)
        )
        if listing is None or listing.id in seen:
            continue
        seen.add(listing.id)
        items.append(listing)
    return items


async def _batch_hydrate_new_auto_ria(ids: list[str]) -> dict[str, ListingOut]:
    """Гідратує нові AUTO.RIA авто через /auto/new/auto/{id}. Кеш: ar-new-info:{id}."""
    if not ids:
        return {}

    from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
    from app.services.auto_ria.mapper import new_info_to_listing

    result: dict[str, ListingOut] = {}
    to_fetch: list[str] = []

    # Читаємо весь батч за один MGET замість N окремих GET
    try:
        redis = await get_redis()
        keys = [f"{_AR_NEW_INFO_PREFIX}{aid}" for aid in ids]
        raws = await redis.mget(*keys)
        for aid, raw in zip(ids, raws):
            if raw:
                try:
                    result[aid] = ListingOut.model_validate(json.loads(raw))
                except Exception:
                    to_fetch.append(aid)
            else:
                to_fetch.append(aid)
    except Exception:
        logger.exception("AR new info cache read failed")
        to_fetch = list(ids)

    if not to_fetch:
        return result

    client = AutoRiaClient()
    sem = asyncio.Semaphore(10)

    async def fetch_one(aid: str) -> tuple[str, ListingOut | None]:
        async with sem:
            try:
                info = await client.get_new_info(aid)
                listing = new_info_to_listing(info)
                return aid, listing
            except (AutoRiaError, Exception):
                return aid, None

    fetched = await asyncio.gather(*(fetch_one(aid) for aid in to_fetch))

    # Зберігаємо в кеш через pipeline
    for aid, listing in fetched:
        if listing:
            result[aid] = listing
    try:
        redis = await get_redis()
        pipe = redis.pipeline(transaction=False)
        for aid, listing in fetched:
            if listing:
                pipe.setex(f"{_AR_NEW_INFO_PREFIX}{aid}", _AR_INFO_TTL_SECONDS, listing.model_dump_json())
        await pipe.execute()
    except Exception:
        pass

    return result


async def _hydrate_page_slots(slots: list[dict]) -> list[ListingOut]:
    """Перетворює слоти сторінки на повні ListingOut об'єкти.

    {"s":"r","i":"..."} — AUTO.RIA вживані, гідрат через /auto/info.
    {"s":"n","i":"..."} — AUTO.RIA нові,   гідрат через /auto/new/auto.
    {"s":"o"/"t","d":{...}} — OLX/Telegram, розпаковуються напряму.
    """
    used_ids = [s["i"] for s in slots if s.get("s") == "r" and "i" in s]
    new_ids = [s["i"] for s in slots if s.get("s") == "n" and "i" in s]

    hydrated_used, hydrated_new = await asyncio.gather(
        _batch_hydrate_auto_ria(used_ids),
        _batch_hydrate_new_auto_ria(new_ids),
    )

    items: list[ListingOut] = []
    for slot in slots:
        src = slot.get("s")
        if src == "r":
            if "d" in slot:
                try:
                    items.append(ListingOut.model_validate(slot["d"]))
                    continue
                except Exception:
                    pass
            listing = hydrated_used.get(slot.get("i", ""))
            if listing:
                items.append(listing)
        elif src == "n":
            if "d" in slot:
                try:
                    items.append(ListingOut.model_validate(slot["d"]))
                    continue
                except Exception:
                    pass
            listing = hydrated_new.get(slot.get("i", ""))
            if listing:
                items.append(listing)
        elif "d" in slot:
            try:
                items.append(ListingOut.model_validate(slot["d"]))
            except Exception:
                pass
    return items


def _search_needs_listing_filter(filters: SearchFilters | None) -> TypeGuard[SearchFilters]:
    if not filters:
        return False
    from app.services.search.filter_multi import effective_regions

    return bool(
        (filters.brand or "").strip()
        or (filters.model or "").strip()
        or effective_regions(filters)
    )


def _filter_listings_by_brand_model(
    items: list[ListingOut],
    filters: SearchFilters,
) -> list[ListingOut]:
    if not _search_needs_listing_filter(filters):
        return items
    from app.services.telegram_channels.mapper import listing_out_matches_filters

    return [item for item in items if listing_out_matches_filters(item, filters)]


async def filter_auto_ria_ids_by_filters(
    auto_ria_ids: list[str],
    filters: SearchFilters,
) -> list[str]:
    """Гідратує AUTO.RIA IDs і лишає лише ті, що проходять brand/model фільтр."""
    if not auto_ria_ids or not _search_needs_listing_filter(filters):
        return auto_ria_ids

    from app.services.telegram_channels.mapper import listing_out_matches_filters

    used_ids = [aid for aid in auto_ria_ids if not aid.startswith("n:")]
    new_ids = [aid[2:] for aid in auto_ria_ids if aid.startswith("n:")]

    hydrated_used, hydrated_new = await asyncio.gather(
        _batch_hydrate_auto_ria(used_ids),
        _batch_hydrate_new_auto_ria(new_ids),
    )

    filtered: list[str] = []
    for aid in auto_ria_ids:
        if aid.startswith("n:"):
            listing = hydrated_new.get(aid[2:])
        else:
            listing = hydrated_used.get(aid)
        if listing and listing_out_matches_filters(listing, filters):
            filtered.append(aid)
    return filtered


async def _collect_matching_listings_from_slots(
    slots: list[dict],
    filters: SearchFilters,
    *,
    limit: int,
    batch_size: int = 20,
) -> list[ListingOut]:
    """Сканує слоти з початку, гідратує пачками, повертає перші limit збігів."""
    from app.services.telegram_channels.mapper import listing_out_matches_filters

    items: list[ListingOut] = []
    idx = 0
    while idx < len(slots) and len(items) < limit:
        batch = slots[idx : idx + batch_size]
        idx += batch_size
        hydrated = await _hydrate_page_slots(batch)
        for listing in hydrated:
            if listing_out_matches_filters(listing, filters):
                items.append(listing)
                if len(items) >= limit:
                    break
    return items


# ---------------------------------------------------------------------------
# Pool pagination
# ---------------------------------------------------------------------------


async def _apply_vin_mirrors_to_page(items: list[ListingOut]) -> list[ListingOut]:
    """Зливає VIN-дублі на сторінці + підтягує дзеркала з БД (AUTO.RIA↔OLX↔Telegram)."""
    if not items:
        return items

    from app.core.database import AsyncSessionLocal
    from app.services.listings.duplicates import (
        collapse_listings_with_db_mirrors,
        enrich_listing_vin_for_dedup,
        mark_duplicates_in_pool,
    )

    enriched = [enrich_listing_vin_for_dedup(item) for item in items]
    merged = mark_duplicates_in_pool(enriched)
    async with AsyncSessionLocal() as db:
        return await collapse_listings_with_db_mirrors(db, merged)


def collapse_pool_totals(
    *,
    slot_total: int,
    unique_count: int,
    page: int,
    per_page: int,
    slot_count: int,
) -> tuple[int, int, int, int | None]:
    """Пагінація після VIN-склеювання.

    Повертає (total карток, pages, offer_count, duplicate_count).
    Якщо весь пул вмістився на сторінку — total = унікальні картки,
    а не сирі слоти джерел (інакше «знайдено 3 / показано 2» і фейкова «Показати ще»).
    """
    offer_count = slot_total
    if page == 1 and slot_count <= per_page:
        dups = max(0, offer_count - unique_count)
        pages = 1 if unique_count else 0
        return unique_count, pages, offer_count, dups
    pages = (slot_total + per_page - 1) // per_page if slot_total else 0
    return slot_total, pages, offer_count, None


async def slice_pool(
    pool: dict[str, Any],
    *,
    page: int,
    per_page: int,
    filters: SearchFilters | None = None,
) -> PaginatedListings:
    """Повертає одну сторінку з пулу, гідратуючи AUTO.RIA-стаби за потреби."""
    slots = pool.get("slots")

    # Зворотна сумісність зі старим форматом (full items list)
    if not slots:
        return _slice_legacy_pool(pool, page=page, per_page=per_page)

    total = int(pool.get("total") or len(slots))
    raw_market = pool.get("market_total")
    market_total = int(raw_market) if raw_market is not None else None
    model_post_filter = bool(pool.get("model_post_filter"))

    start = (page - 1) * per_page
    end = start + per_page

    if model_post_filter and _search_needs_listing_filter(filters):
        items = await _collect_matching_listings_from_slots(slots, filters, limit=end)
        items = items[start:end]
        market_total = None
    else:
        page_slots = slots[start:end]
        items = await _hydrate_page_slots(page_slots)
        if _search_needs_listing_filter(filters):
            from app.services.telegram_channels.mapper import listing_out_matches_filters

            items = [item for item in items if listing_out_matches_filters(item, filters)]

    items = await _apply_vin_mirrors_to_page(items)

    total, pages, offer_count, duplicate_count = collapse_pool_totals(
        slot_total=total,
        unique_count=len(items),
        page=page,
        per_page=per_page,
        slot_count=len(slots),
    )

    sources_raw = pool.get("sources") or []
    sources = [SourceStatusOut.model_validate(row) for row in sources_raw]

    return PaginatedListings(
        items=items,
        total=total,
        market_total=market_total if market_total and market_total > total else None,
        page=page,
        per_page=per_page,
        pages=pages,
        sources=sources,
        partial=bool(pool.get("partial")),
        from_cache=True,
        offer_count=offer_count,
        duplicate_count=duplicate_count,
    )


def _slice_legacy_pool(
    pool: dict[str, Any],
    *,
    page: int,
    per_page: int,
) -> PaginatedListings:
    """Старий формат пулу (items — повні об'єкти). Для зворотної сумісності."""
    raw_items = pool.get("items") or []
    total = int(pool.get("total") or len(raw_items))
    raw_market = pool.get("market_total")
    market_total = int(raw_market) if raw_market is not None else None
    start = (page - 1) * per_page
    end = start + per_page
    page_raw = raw_items[start:end]
    items = [ListingOut.model_validate(row) for row in page_raw]
    pages = (total + per_page - 1) // per_page if total else 0

    sources_raw = pool.get("sources") or []
    sources = [SourceStatusOut.model_validate(row) for row in sources_raw]

    return PaginatedListings(
        items=items,
        total=total,
        market_total=market_total if market_total and market_total > total else None,
        page=page,
        per_page=per_page,
        pages=pages,
        sources=sources,
        partial=bool(pool.get("partial")),
        from_cache=True,
    )


async def try_load_pool_listings(
    filters: SearchFilters,
    sort_by: str,
    *,
    max_items: int,
    alt_sorts: tuple[str, ...] = ("newest", "published_desc"),
) -> list[ListingOut] | None:
    """Повертає items з live-pool кешу, якщо є (для моніторингу / dedupe)."""
    seen: set[str] = set()
    for sort in (sort_by, *alt_sorts):
        if sort in seen:
            continue
        seen.add(sort)
        pool = await get_live_pool(filters, sort)
        if not pool:
            continue

        # Новий формат: slots
        slots = pool.get("slots")
        if slots:
            if _search_needs_listing_filter(filters):
                items = await _collect_matching_listings_from_slots(
                    slots[:max_items * 3],
                    filters,
                    limit=max_items,
                )
            else:
                page_slots = slots[:max_items]
                items = await _hydrate_page_slots(page_slots)
            if items:
                return items[:max_items]

        # Старий формат: items
        raw_items = pool.get("items")
        if raw_items:
            items_out: list[ListingOut] = []
            for row in raw_items[:max_items]:
                try:
                    items_out.append(ListingOut.model_validate(row))
                except Exception:
                    continue
            if items_out:
                return items_out

    return None
