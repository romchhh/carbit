"""KV-кеш повного пулу live-пошуку — пагінація без повторних запитів до джерел.

Slot-based pool format (Redis):
  {
    "slots": [
      {"s": "r", "i": "12345", "d": {...}?},  # AUTO.RIA: ID + опційна HTML-картка; деталі — /auto/info
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

LIVE_POOL_PREFIX = "live-pool:v7:"
LIVE_POOL_TTL_SECONDS = 600  # 10 хвилин — повторний пошук без нових AR-запитів
# Максимальна кількість слотів у пулі (AUTO.RIA IDs + OLX/Telegram items)
LIVE_POOL_SIZE = 2500

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
    beta_cursor: dict | None = None,
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
            "beta_cursor": beta_cursor,
            "sort_by": sort_by,
        }
        await redis.setex(
            live_pool_cache_key(filters, sort_by),
            ttl_seconds,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        logger.exception("Live pool cache write failed")


_beta_extend_locks: dict[str, asyncio.Lock] = {}


def _html_slot_keys(slots: list[dict]) -> set[str]:
    keys: set[str] = set()
    for slot in slots:
        src = slot.get("s")
        if src == "r":
            raw = str(slot.get("i") or "")
            if raw.isdigit():
                keys.add(raw)
            continue
        if src == "n":
            raw = str(slot.get("i") or "")
            if raw.isdigit():
                keys.add(f"n:{raw}")
            continue
        if src != "b":
            continue
        data = slot.get("d") or {}
        raw = str(data.get("id") or "")
        if raw.startswith("new_auto_ria_"):
            suffix = raw.removeprefix("new_auto_ria_")
            if suffix.isdigit():
                keys.add(f"n:{suffix}")
            continue
        suffix = raw.removeprefix("auto_ria_beta_").removeprefix("auto_ria_")
        if suffix.isdigit():
            keys.add(suffix)
    return keys


def _html_slot_new_stock_fps(slots: list[dict]) -> set[str]:
    from app.services.listings.duplicates import auto_ria_new_stock_fingerprint

    fps: set[str] = set()
    for slot in slots:
        listing = _slot_listing(slot)
        if listing is None:
            continue
        fp = auto_ria_new_stock_fingerprint(listing)
        if fp:
            fps.add(fp)
    return fps


async def ensure_beta_pool_covers(
    pool: dict[str, Any],
    *,
    filters: SearchFilters,
    sort_by: str,
    need: int,
) -> dict[str, Any]:
    """Довантажує наступні HTML-сторінки AUTO.RIA, коли користувач гортає далі."""
    cursor = pool.get("beta_cursor")
    if not isinstance(cursor, dict) or cursor.get("exhausted"):
        return pool

    slots = list(pool.get("slots") or [])
    if need <= len(slots):
        return pool

    from app.services.auto_ria_beta.constants import MAX_PAGES, PAGE_SIZE, POOL_MAX_ITEMS
    from app.services.auto_ria_beta.service import fetch_auto_ria_beta_batch

    key = live_pool_cache_key(filters, sort_by)
    lock = _beta_extend_locks.setdefault(key, asyncio.Lock())
    async with lock:
        fresh = await get_live_pool(filters, sort_by)
        if isinstance(fresh, dict):
            pool = fresh
        cursor = pool.get("beta_cursor") if isinstance(pool.get("beta_cursor"), dict) else cursor
        slots = list(pool.get("slots") or [])
        if not isinstance(cursor, dict) or cursor.get("exhausted") or need <= len(slots):
            return pool

        seen = _html_slot_keys(slots)
        seen_fps = _html_slot_new_stock_fps(slots)
        next_html = int(cursor.get("next_html_page") or 0)
        market_total = int(pool.get("market_total") or 0)
        while len(slots) < need and next_html < MAX_PAGES and len(slots) < POOL_MAX_ITEMS:
            batch = await fetch_auto_ria_beta_batch(
                filters,
                sort_by=sort_by,
                start_page=next_html,
                html_pages=1,
                need=PAGE_SIZE,
                seen_ids=seen,
            )
            next_html = batch.next_html_page
            market_total = max(market_total, batch.market_total)
            if batch.error:
                cursor = {
                    "next_html_page": next_html,
                    "exhausted": True,
                }
                break
            from app.services.auto_ria.html_merge import listing_numeric_id
            from app.services.listings.duplicates import auto_ria_new_stock_fingerprint

            for listing in batch.listings:
                aid = listing_numeric_id(listing)
                if not aid or aid in seen:
                    continue
                fp = auto_ria_new_stock_fingerprint(listing)
                if fp and fp in seen_fps:
                    continue
                seen.add(aid)
                if fp:
                    seen_fps.add(fp)
                if aid.startswith("n:"):
                    slots.append({"s": "n", "i": aid[2:], "d": listing.model_dump(mode="json")})
                else:
                    slots.append({"s": "r", "i": aid, "d": listing.model_dump(mode="json")})
            cursor = {
                "next_html_page": next_html,
                "exhausted": bool(batch.exhausted),
            }
            if batch.exhausted:
                break
            if not batch.listings:
                cursor = {
                    "next_html_page": next_html,
                    "exhausted": True,
                }
                break

        extra = 0
        if cursor and not cursor.get("exhausted"):
            extra = max(0, market_total - len(slots))
        nav_total = len(slots) + extra
        pool = {
            **pool,
            "slots": slots,
            "beta_cursor": cursor,
            "total": nav_total,
            "market_total": market_total or pool.get("market_total"),
        }
        await set_live_pool(
            filters,
            sort_by,
            slots=slots,
            total=nav_total,
            market_total=pool.get("market_total"),
            sources=pool.get("sources") or [],
            partial=bool(pool.get("partial")),
            model_post_filter=bool(pool.get("model_post_filter")),
            beta_cursor=cursor,
        )
        return pool


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
    html_cards: dict[str, ListingOut] | None = None,
) -> list[ListingOut]:
    """Гідратує tagged IDs (`123` вживані, `n:456` нові) зі спільним Redis-кешем."""
    from app.services.auto_ria.html_merge import merge_html_card_with_api

    tagged = list(ids[:limit] if limit is not None else ids)
    if not tagged:
        return []
    cards = html_cards or {}
    used_ids = [aid for aid in tagged if not aid.startswith("n:")]
    new_ids = [aid[2:] for aid in tagged if aid.startswith("n:")]
    hydrated_used, hydrated_new = await asyncio.gather(
        _batch_hydrate_auto_ria(used_ids),
        _batch_hydrate_new_auto_ria(new_ids),
    )
    items: list[ListingOut] = []
    seen: set[str] = set()
    for aid in tagged:
        raw = aid[2:] if aid.startswith("n:") else aid
        listing = hydrated_new.get(raw) if aid.startswith("n:") else hydrated_used.get(aid)
        html = cards.get(raw)
        if listing and html:
            listing = merge_html_card_with_api(html, listing)
        elif listing is None:
            listing = html
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


def _slot_listing(slot: dict) -> ListingOut | None:
    raw = slot.get("d")
    if not raw:
        return None
    try:
        return ListingOut.model_validate(raw)
    except Exception:
        return None


async def _hydrate_page_slots(slots: list[dict]) -> list[ListingOut]:
    """Перетворює слоти сторінки на повні ListingOut об'єкти.

    {"s":"r","i":"...","d":?} — AUTO.RIA вживані: завжди /auto/info, HTML-картка зливається.
    {"s":"n","i":"..."} — AUTO.RIA нові,   гідрат через /auto/new/auto.
    {"s":"o"/"t","d":{...}} — OLX/Telegram, розпаковуються напряму.
    """
    from app.services.auto_ria.html_merge import merge_html_card_with_api

    used_ids = [
        s["i"]
        for s in slots
        if s.get("s") == "r" and "i" in s and not str(s.get("i", "")).startswith("beta_")
    ]
    new_ids = [s["i"] for s in slots if s.get("s") == "n" and "i" in s]

    hydrated_used, hydrated_new = await asyncio.gather(
        _batch_hydrate_auto_ria(used_ids),
        _batch_hydrate_new_auto_ria(new_ids),
    )

    items: list[ListingOut] = []
    for slot in slots:
        src = slot.get("s")
        if src == "r":
            html = _slot_listing(slot)
            api = hydrated_used.get(slot.get("i", ""))
            if api and html:
                items.append(merge_html_card_with_api(html, api))
            elif api:
                items.append(api)
            elif html:
                items.append(html)
        elif src == "n":
            html = _slot_listing(slot)
            api = hydrated_new.get(slot.get("i", ""))
            if api and html:
                items.append(merge_html_card_with_api(html, api))
            elif api:
                items.append(api)
            elif html:
                items.append(html)
        elif "d" in slot:
            listing = _slot_listing(slot)
            if listing:
                items.append(listing)
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


async def _collect_unique_page_items(
    pool: dict[str, Any],
    *,
    filters: SearchFilters | None,
    sort_by: str,
    page: int,
    per_page: int,
    apply_listing_filter: bool,
) -> tuple[list[ListingOut], dict[str, Any]]:
    """Гідратує слоти, добирає унікальні картки до per_page, сортує сторінку."""
    from app.services.auto_ria.mapper import sort_listings
    from app.services.listings.duplicates import mark_duplicates_in_pool
    from app.services.telegram_channels.mapper import listing_out_matches_filters

    skip = max(page - 1, 0) * per_page
    want = skip + per_page
    kept: list[ListingOut] = []
    idx = 0
    max_scan = max(skip + per_page * 5, per_page * 2)

    while len(kept) < want:
        slots = list(pool.get("slots") or [])
        if idx >= len(slots):
            if filters is None or idx >= max_scan:
                break
            before = len(slots)
            pool = await ensure_beta_pool_covers(
                pool,
                filters=filters,
                sort_by=sort_by,
                need=before + 1,
            )
            slots = list(pool.get("slots") or [])
            if len(slots) <= before:
                break
            max_scan = max(max_scan, len(slots))
            continue
        if idx >= max_scan:
            break
        batch = slots[idx : idx + per_page]
        idx += len(batch)
        if not batch:
            break
        hydrated = await _hydrate_page_slots(batch)
        if apply_listing_filter and filters is not None:
            hydrated = [row for row in hydrated if listing_out_matches_filters(row, filters)]
        hydrated = await _apply_vin_mirrors_to_page(hydrated)
        kept = mark_duplicates_in_pool([*kept, *hydrated])

    page_items = kept[skip : skip + per_page]
    return sort_listings(page_items, sort_by), pool


async def slice_pool(
    pool: dict[str, Any],
    *,
    page: int,
    per_page: int,
    filters: SearchFilters | None = None,
    sort_by: str = "newest",
) -> PaginatedListings:
    """Повертає одну сторінку з пулу, гідратуючи AUTO.RIA-стаби за потреби."""
    slots = pool.get("slots")

    # Зворотна сумісність зі старим форматом (full items list)
    if not slots and not pool.get("beta_cursor"):
        return _slice_legacy_pool(pool, page=page, per_page=per_page)

    if filters is not None:
        need = page * per_page * 2
        pool = await ensure_beta_pool_covers(
            pool, filters=filters, sort_by=sort_by, need=need
        )
        slots = pool.get("slots") or []

    if not isinstance(slots, list):
        slots = []

    total = int(pool.get("total") or len(slots))
    raw_market = pool.get("market_total")
    market_total = int(raw_market) if raw_market is not None else None
    model_post_filter = bool(pool.get("model_post_filter"))
    apply_listing_filter = bool(
        model_post_filter or _search_needs_listing_filter(filters)
    )

    items, pool = await _collect_unique_page_items(
        pool,
        filters=filters,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
        apply_listing_filter=apply_listing_filter,
    )
    slots = list(pool.get("slots") or [])
    if model_post_filter:
        market_total = None

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
