from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.mapper import sort_listings
from app.services.auto_ria.service import search_auto_ria
from app.services.imperiya.errors import ImperiyaError
from app.services.imperiya.service import search_imperiya
from app.services.olx.errors import OlxError
from app.services.olx.service import _search_olx_body
from app.services.search.concurrency import acquire_olx_slot
from app.services.telegram.admin_alerts import notify_admin_parsing_error
from app.services.telegram_channels.ingest import search_telegram_listings

IMPLEMENTED_SOURCES = {"auto_ria", "olx", "telegram", "imperiya"}
# Бюджет лише на HTTP-сканування після acquire_olx_slot (черга не входить у wait_for).
OLX_SEARCH_TIMEOUT_SECONDS = 22.0
# Скільки оголошень тягнути з кожного джерела в спільний пул (режим «Шукати всі»).
SOURCE_POOL_CAP = 500
TELEGRAM_POOL_CAP = 500
TELEGRAM_MAX_SCAN = 4000
AUTO_RIA_PAGE_SIZE = 50
# Live pool збирає лише IDs — 25 с достатньо; 90 с тримало весь gather.
AUTO_RIA_POOL_TIMEOUT_SECONDS = 25.0
IMPERIYA_POOL_TIMEOUT_SECONDS = 25.0
IMPERIYA_PAGE_SIZE = 50
# TG — лише БД (без keyword refresh на live-пошуку).
TELEGRAM_POOL_TIMEOUT_SECONDS = 12.0
# У змішаній видачі спочатку OLX/Telegram, щоб перші картки не були лише з AUTO.RIA.
_SOURCE_BLEND_ORDER = {"olx": 0, "imperiya": 1, "telegram": 2, "auto_ria": 3}
_DATE_SORT_KEYS = frozenset({"newest", "published_desc"})

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceSearchStatus:
    source: str
    item_count: int
    error: str | None = None


@dataclass(frozen=True)
class SearchListingsOutcome:
    result: PaginatedListings
    sources: list[SourceSearchStatus]


def normalize_sources(sources: list[str] | None) -> list[str]:
    default = ["auto_ria", "olx", "imperiya"]
    if app_settings.TELEGRAM_ENABLED:
        default.append("telegram")

    if not sources:
        return default

    normalized: list[str] = []
    for raw in sources:
        key = raw.strip().lower().replace(".", "_").replace(" ", "_")
        if key in ("auto_ria", "autoria"):
            normalized.append("auto_ria")
        elif key == "olx":
            normalized.append("olx")
        elif key in ("imperiya", "imperiya_auto", "imperiya-auto", "iautos"):
            normalized.append("imperiya")
        elif key == "telegram":
            normalized.append("telegram")

    deduped: list[str] = []
    for item in normalized:
        if item in IMPLEMENTED_SOURCES and item not in deduped:
            deduped.append(item)
    return deduped or default


def _empty_page(page: int, per_page: int) -> PaginatedListings:
    return PaginatedListings(items=[], total=0, page=page, per_page=per_page, pages=0)


def _interleave_by_source(
    batches: list[tuple[str, list[ListingOut]]],
    *,
    limit: int,
) -> list[ListingOut]:
    """Round-robin по джерелах: рівна видимість OLX / Telegram / AUTO.RIA."""
    if not batches:
        return []

    if len(batches) == 1:
        return batches[0][1][:limit]

    batches = sorted(batches, key=lambda row: _SOURCE_BLEND_ORDER.get(row[0], 99))
    queues = {source: list(items) for source, items in batches}
    order = [source for source, _ in batches]
    merged: list[ListingOut] = []
    seen_ids: set[str] = set()

    while len(merged) < limit:
        added = False
        for source in order:
            if len(merged) >= limit:
                break
            queue = queues[source]
            while queue:
                candidate = queue.pop(0)
                if candidate.id in seen_ids:
                    continue
                merged.append(candidate)
                seen_ids.add(candidate.id)
                added = True
                break
        if not added:
            break

    return merged


def _sorted_merge_slice(
    batches: list[tuple[str, PaginatedListings]],
    *,
    page: int,
    per_page: int,
    sort_by: str,
) -> tuple[list[ListingOut], int, int]:
    """Зливає джерела в один список і сортує глобально (newest / ціна / тощо).

    Повертає (page_items, nav_total, market_total).
    """
    source_totals = 0
    merged: list[ListingOut] = []
    seen_ids: set[str] = set()

    for _source, result in batches:
        source_totals += result.total
        for item in result.items:
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            merged.append(item)

    from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

    merged = dedupe_telegram_posts_in_pool(merged)
    seen_ids.clear()
    unique: list[ListingOut] = []
    for item in merged:
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        unique.append(item)
    merged_items = sort_listings(unique, sort_by)

    start = (page - 1) * per_page
    end = start + per_page
    page_items = merged_items[start:end]

    pool_size = len(merged_items)
    if page_items and len(page_items) < per_page:
        nav_total = start + len(page_items)
    else:
        nav_total = max(source_totals, pool_size)
        if start + per_page >= pool_size:
            nav_total = pool_size
    return page_items, nav_total, source_totals


def _fair_merge_slice(
    batches: list[tuple[str, PaginatedListings]],
    *,
    page: int,
    per_page: int,
    sort_by: str,
) -> tuple[list[ListingOut], int, int]:
    """Зливає джерела round-robin (OLX → TG → AR), усередині кожного — sort_by.

    Для моніторингу / «новіші» не дає AUTO.RIA витіснити OLX/Telegram лише через свіжіші дати.
    """
    source_totals = sum(result.total for _, result in batches)
    per_source: list[tuple[str, list[ListingOut]]] = []
    for source, result in batches:
        if not result.items:
            continue
        per_source.append((source, sort_listings(list(result.items), sort_by)))

    if not per_source:
        return [], 0, 0

    pool_cap = max(SOURCE_POOL_CAP, page * per_page * 2)
    merged = _interleave_by_source(per_source, limit=pool_cap)

    from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

    merged = dedupe_telegram_posts_in_pool(merged)
    seen_ids: set[str] = set()
    unique: list[ListingOut] = []
    for item in merged:
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        unique.append(item)

    start = (page - 1) * per_page
    page_items = unique[start : start + per_page]
    pool_size = len(unique)

    if page_items and len(page_items) < per_page:
        nav_total = start + len(page_items)
    else:
        nav_total = max(source_totals, pool_size)
        if start + per_page >= pool_size:
            nav_total = pool_size
    return page_items, nav_total, source_totals


def _merge_multi_source_page(
    batches: list[tuple[str, PaginatedListings]],
    *,
    page: int,
    per_page: int,
    sort_by: str,
) -> tuple[list[ListingOut], int, int]:
    if sort_by in _DATE_SORT_KEYS:
        return _fair_merge_slice(batches, page=page, per_page=per_page, sort_by=sort_by)
    return _sorted_merge_slice(batches, page=page, per_page=per_page, sort_by=sort_by)


def _published_max_age(filters: SearchFilters):
    from datetime import timedelta

    if filters.published_within_hours:
        return timedelta(hours=filters.published_within_hours)
    if filters.published_within_days:
        return timedelta(days=filters.published_within_days)
    return None


def _filter_listings_by_published_age(
    items: list[ListingOut],
    max_age,
) -> list[ListingOut]:
    if not max_age:
        return items

    from app.core.timezone import as_kyiv, now_kyiv

    cutoff = now_kyiv() - max_age
    filtered: list[ListingOut] = []
    for item in items:
        try:
            published = as_kyiv(item.published_at)
        except Exception:
            continue
        if published >= cutoff:
            filtered.append(item)
    return filtered


def _filter_listings_by_published_days(
    items: list[ListingOut],
    days: int | None,
) -> list[ListingOut]:
    if not days:
        return items
    from datetime import timedelta

    return _filter_listings_by_published_age(items, timedelta(days=days))


def _filter_page_by_published_within_days(
    result: PaginatedListings,
    *,
    days: int | None,
) -> PaginatedListings:
    if not days:
        return result

    filtered = _filter_listings_by_published_days(result.items, days)
    total = len(filtered)
    pages = (total + result.per_page - 1) // result.per_page if total else 0
    return PaginatedListings(
        items=filtered,
        total=total,
        page=result.page,
        per_page=result.per_page,
        pages=pages,
    )


async def _search_single_source(
    source: str,
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    db=None,
    keyword_refresh: bool = False,
    olx_enrich_details: bool = True,
    telegram_found_after: datetime | None = None,
) -> PaginatedListings:
    if source == "telegram":
        if db is not None:
            return await search_telegram_listings(
                db,
                filters,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                max_scan=TELEGRAM_MAX_SCAN,
                keyword_refresh=keyword_refresh,
                found_after=telegram_found_after,
            )
        async with AsyncSessionLocal() as session:
            return await search_telegram_listings(
                session,
                filters,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                max_scan=TELEGRAM_MAX_SCAN,
                keyword_refresh=keyword_refresh,
                found_after=telegram_found_after,
            )
    if source == "olx":
        async with acquire_olx_slot():
            return await _search_olx_body(
                filters,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                enrich_details=olx_enrich_details,
                use_cache=use_cache,
                cache_ttl_seconds=cache_ttl_seconds,
            )
    if source == "imperiya":
        return await search_imperiya(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )
    return await search_auto_ria(
        filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        use_cache=use_cache,
        cache_ttl_seconds=cache_ttl_seconds,
    )


async def _fetch_source_pool(
    source: str,
    filters: SearchFilters,
    *,
    need: int,
    sort_by: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    db=None,
    keyword_refresh: bool = False,
    olx_enrich_details: bool = True,
    telegram_found_after: datetime | None = None,
) -> PaginatedListings:
    """Тягне пул оголошень з джерела (кілька сторінок AUTO.RIA за потреби)."""
    from app.services.search.filter_multi import expand_filters_for_api_fetch, needs_api_fanout

    need = max(need, 1)
    if source in ("auto_ria", "olx", "imperiya") and needs_api_fanout(filters):
        variants = expand_filters_for_api_fetch(filters)
        per_variant = max(need // len(variants), 20)
        chunks = await asyncio.gather(
            *[
                _fetch_source_pool(
                    source,
                    variant,
                    need=per_variant,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    db=db,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                    telegram_found_after=telegram_found_after,
                )
                for variant in variants
            ]
        )
        seen: set[str] = set()
        merged: list[ListingOut] = []
        total = 0
        for chunk in chunks:
            total = max(total, chunk.total)
            for item in chunk.items:
                if item.id in seen:
                    continue
                seen.add(item.id)
                merged.append(item)
                if len(merged) >= need:
                    break
            if len(merged) >= need:
                break
        merged = sort_listings(merged[:need], sort_by)
        pages = (total + need - 1) // need if total else 0
        return PaginatedListings(
            items=merged,
            total=max(total, len(merged)),
            page=1,
            per_page=need,
            pages=pages,
        )

    if source == "telegram":
        return await _search_single_source(
            source,
            filters,
            page=1,
            per_page=need,
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
            db=db,
            keyword_refresh=keyword_refresh,
            olx_enrich_details=olx_enrich_details,
            telegram_found_after=telegram_found_after,
        )

    if source == "olx":
        return await _search_single_source(
            source,
            filters,
            page=1,
            per_page=need,
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
            db=db,
            keyword_refresh=keyword_refresh,
            olx_enrich_details=olx_enrich_details,
        )

    if source == "imperiya":
        collected: list[ListingOut] = []
        seen: set[str] = set()
        total = 0
        page = 1
        max_pages = max((need + IMPERIYA_PAGE_SIZE - 1) // IMPERIYA_PAGE_SIZE, 1)
        while len(collected) < need and page <= max_pages:
            chunk = await _search_single_source(
                source,
                filters,
                page=page,
                per_page=min(IMPERIYA_PAGE_SIZE, need - len(collected)),
                sort_by=sort_by,
                use_cache=use_cache,
                cache_ttl_seconds=cache_ttl_seconds,
            )
            total = max(total, chunk.total)
            for item in chunk.items:
                if item.id in seen:
                    continue
                seen.add(item.id)
                collected.append(item)
                if len(collected) >= need:
                    break
            if len(chunk.items) < IMPERIYA_PAGE_SIZE:
                break
            page += 1
        collected = sort_listings(collected[:need], sort_by)
        pages = (total + need - 1) // need if total else 0
        return PaginatedListings(
            items=collected,
            total=max(total, len(collected)),
            page=1,
            per_page=need,
            pages=pages,
            market_total=total,
        )

    # AUTO.RIA: countpage ≤ 50 — збираємо кілька сторінок
    collected: list[ListingOut] = []
    seen: set[str] = set()
    total = 0
    page = 1
    max_pages = max((need + AUTO_RIA_PAGE_SIZE - 1) // AUTO_RIA_PAGE_SIZE, 1)

    while len(collected) < need and page <= max_pages:
        chunk = await _search_single_source(
            source,
            filters,
            page=page,
            per_page=min(AUTO_RIA_PAGE_SIZE, need - len(collected)),
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
            db=db,
            keyword_refresh=keyword_refresh,
            olx_enrich_details=olx_enrich_details,
        )
        total = max(total, chunk.total)
        if not chunk.items:
            break
        for item in chunk.items:
            if item.id in seen:
                continue
            seen.add(item.id)
            collected.append(item)
            if len(collected) >= need:
                break
        if len(chunk.items) < chunk.per_page:
            break
        page += 1

    pages = (total + need - 1) // need if total else 0
    return PaginatedListings(
        items=collected[:need],
        total=total,
        page=1,
        per_page=need,
        pages=pages,
    )


async def _search_olx_safe(
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> tuple[PaginatedListings, str | None]:
    """OLX не повинен ламати весь пошук — таймаут/помилки дають порожню видачу.

    Семафор займається заздалегідь; таймаут стосується лише фактичного HTTP-сканування.
    """
    try:
        async with acquire_olx_slot():
            result = await asyncio.wait_for(
                _search_olx_body(
                    filters,
                    page=page,
                    per_page=per_page,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                ),
                timeout=OLX_SEARCH_TIMEOUT_SECONDS,
            )
        return result, None
    except asyncio.TimeoutError:
        return _empty_page(page, per_page), f"таймаут {OLX_SEARCH_TIMEOUT_SECONDS:.0f}s"
    except OlxError as exc:
        return _empty_page(page, per_page), str(exc)
    except Exception as exc:
        return _empty_page(page, per_page), str(exc)


def _pick_primary_error(errors: list[Exception]) -> Exception:
    for preferred in (AutoRiaError, ValueError, OlxError):
        for error in errors:
            if isinstance(error, preferred):
                return error
    return errors[0]


def _source_label(source: str) -> str:
    if source == "auto_ria":
        return "AUTO.RIA"
    if source == "imperiya":
        return "Імперія Авто"
    if source == "telegram":
        return "Telegram"
    return source.upper()


def _search_filters_summary(filters: SearchFilters) -> str:
    parts: list[str] = []
    if filters.brand:
        parts.append(filters.brand)
    if filters.model:
        parts.append(filters.model)
    if filters.region:
        parts.append(filters.region)
    if filters.price_from is not None or filters.price_to is not None:
        parts.append(
            f"ціна {filters.price_from if filters.price_from is not None else '—'}-"
            f"{filters.price_to if filters.price_to is not None else '—'}"
        )
    return ", ".join(parts) or "без фільтрів"


def _olx_timeout_partial_error(error: str | None) -> bool:
    err = (error or "").lower()
    return "таймаут" in err or "timeout" in err


async def _notify_partial_source_failures(
    source_statuses: list[SourceSearchStatus],
    filters: SearchFilters,
) -> None:
    """Сповіщає адміна, коли одне джерело впало, але пошук повернув інші результати."""
    failed = [status for status in source_statuses if status.error]
    if not failed:
        return
    if not any(status.item_count > 0 for status in source_statuses):
        return

    details = f"Частковий пошук: {_search_filters_summary(filters)}"
    for status in failed:
        err = status.error or "невідома помилка"
        # OLX часто не встигає на широких фільтрах; AUTO.RIA/TG уже дали видачу — не спамимо.
        if status.source.upper() == "OLX" and _olx_timeout_partial_error(err):
            logger.warning("OLX partial timeout (skipped admin alert): %s | %s", err, details)
            continue
        await notify_admin_parsing_error(
            source=status.source,
            error=err,
            details=details,
        )


async def search_listings_outcome(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    db=None,
    keyword_refresh: bool = False,
    olx_enrich_details: bool = True,
    telegram_found_after: datetime | None = None,
) -> SearchListingsOutcome:
    from app.services.search.brand_model_keywords import normalize_search_filters

    filters = normalize_search_filters(filters)
    sources = normalize_sources(filters.sources)
    source_statuses: list[SourceSearchStatus] = []
    max_age = _published_max_age(filters)

    if len(sources) == 1:
        source = sources[0]
        from app.services.search.filter_multi import needs_api_fanout

        try:
            if max_age:
                raw = await _search_single_source(
                    source,
                    filters,
                    page=1,
                    per_page=per_page * max(page, 1) * 3,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    db=db,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                    telegram_found_after=telegram_found_after,
                )
                filtered = sort_listings(
                    _filter_listings_by_published_age(raw.items, max_age),
                    sort_by,
                )
                start = (page - 1) * per_page
                page_items = filtered[start : start + per_page]
                total = len(filtered)
                pages = (total + per_page - 1) // per_page if total else 0
                result = PaginatedListings(
                    items=page_items,
                    total=total,
                    page=page,
                    per_page=per_page,
                    pages=pages,
                )
            elif source in ("auto_ria", "olx", "imperiya") and needs_api_fanout(filters):
                pool_need = per_page * max(page, 1)
                pool = await _fetch_source_pool(
                    source,
                    filters,
                    need=pool_need,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    db=db,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                    telegram_found_after=telegram_found_after,
                )
                start = (page - 1) * per_page
                page_items = pool.items[start : start + per_page]
                total = max(pool.total, len(pool.items))
                pages = (total + per_page - 1) // per_page if total else 0
                result = PaginatedListings(
                    items=page_items,
                    total=total,
                    page=page,
                    per_page=per_page,
                    pages=pages,
                )
            else:
                result = await _search_single_source(
                    source,
                    filters,
                    page=page,
                    per_page=per_page,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    db=db,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                    telegram_found_after=telegram_found_after,
                )
        except Exception as exc:
            source_statuses.append(
                SourceSearchStatus(source=_source_label(source), item_count=0, error=str(exc))
            )
            raise _pick_primary_error([exc]) from exc

        source_statuses.append(
            SourceSearchStatus(source=_source_label(source), item_count=len(result.items))
        )
        return SearchListingsOutcome(result=result, sources=source_statuses)

    # Для «Шукати всі» тягнемо пул з кожного джерела і змішуємо fair interleave
    fetch_multiplier = 3 if max_age else 2
    pool_need = min(SOURCE_POOL_CAP, per_page * max(page, 1) * fetch_multiplier)
    telegram_need = min(TELEGRAM_POOL_CAP, max(pool_need, per_page * max(page, 1) * 5))
    errors: list[Exception] = []
    successful: list[tuple[str, PaginatedListings]] = []

    async def run_auto_ria() -> PaginatedListings | Exception:
        try:
            return await asyncio.wait_for(
                _fetch_source_pool(
                    "auto_ria",
                    filters,
                    need=pool_need,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                ),
                timeout=AUTO_RIA_POOL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return TimeoutError(f"AUTO.RIA: таймаут {AUTO_RIA_POOL_TIMEOUT_SECONDS:.0f}s")
        except Exception as exc:
            return exc

    async def run_olx() -> tuple[PaginatedListings, str | None]:
        try:
            async with acquire_olx_slot():
                result = await asyncio.wait_for(
                    _search_olx_body(
                        filters,
                        page=1,
                        per_page=pool_need,
                        sort_by=sort_by,
                        enrich_details=olx_enrich_details,
                        use_cache=use_cache,
                        cache_ttl_seconds=cache_ttl_seconds,
                    ),
                    timeout=OLX_SEARCH_TIMEOUT_SECONDS,
                )
            return result, None
        except asyncio.TimeoutError:
            return _empty_page(1, pool_need), f"таймаут {OLX_SEARCH_TIMEOUT_SECONDS:.0f}s"
        except OlxError as exc:
            return _empty_page(1, pool_need), str(exc)
        except Exception as exc:
            return _empty_page(1, pool_need), str(exc)

    async def run_imperiya() -> PaginatedListings | Exception:
        try:
            return await asyncio.wait_for(
                _fetch_source_pool(
                    "imperiya",
                    filters,
                    need=pool_need,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                ),
                timeout=IMPERIYA_POOL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return TimeoutError(f"Імперія Авто: таймаут {IMPERIYA_POOL_TIMEOUT_SECONDS:.0f}s")
        except Exception as exc:
            return exc

    async def run_telegram() -> PaginatedListings | Exception:
        try:
            # Окрема сесія: AsyncSession не можна ділити між asyncio.gather
            return await asyncio.wait_for(
                _fetch_source_pool(
                    "telegram",
                    filters,
                    need=telegram_need,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    db=db,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
                    telegram_found_after=telegram_found_after,
                ),
                timeout=TELEGRAM_POOL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return TimeoutError(f"Telegram: таймаут {TELEGRAM_POOL_TIMEOUT_SECONDS:.0f}s")
        except Exception as exc:
            return exc

    tasks: list[asyncio.Task] = []
    if "auto_ria" in sources:
        tasks.append(asyncio.create_task(run_auto_ria()))
    if "olx" in sources:
        tasks.append(asyncio.create_task(run_olx()))
    if "imperiya" in sources:
        tasks.append(asyncio.create_task(run_imperiya()))
    if "telegram" in sources:
        tasks.append(asyncio.create_task(run_telegram()))

    raw_results = await asyncio.gather(*tasks)

    result_index = 0
    if "auto_ria" in sources:
        auto_ria_out = raw_results[result_index]
        result_index += 1
        if isinstance(auto_ria_out, Exception):
            errors.append(auto_ria_out)
            source_statuses.append(
                SourceSearchStatus(
                    source="AUTO.RIA",
                    item_count=0,
                    error=str(auto_ria_out),
                )
            )
        else:
            successful.append(("auto_ria", auto_ria_out))
            source_statuses.append(
                SourceSearchStatus(source="AUTO.RIA", item_count=len(auto_ria_out.items))
            )

    if "olx" in sources:
        olx_out, olx_error = raw_results[result_index]
        result_index += 1
        successful.append(("olx", olx_out))
        source_statuses.append(
            SourceSearchStatus(
                source="OLX",
                item_count=len(olx_out.items),
                error=olx_error,
            )
        )

    if "imperiya" in sources:
        imperiya_out = raw_results[result_index]
        result_index += 1
        if isinstance(imperiya_out, Exception):
            errors.append(imperiya_out)
            source_statuses.append(
                SourceSearchStatus(
                    source="Імперія Авто",
                    item_count=0,
                    error=str(imperiya_out),
                )
            )
        else:
            successful.append(("imperiya", imperiya_out))
            source_statuses.append(
                SourceSearchStatus(source="Імперія Авто", item_count=len(imperiya_out.items))
            )

    if "telegram" in sources:
        telegram_out = raw_results[result_index]
        if isinstance(telegram_out, Exception):
            errors.append(telegram_out)
            source_statuses.append(
                SourceSearchStatus(
                    source="Telegram",
                    item_count=0,
                    error=str(telegram_out),
                )
            )
        else:
            successful.append(("telegram", telegram_out))
            source_statuses.append(
                SourceSearchStatus(source="Telegram", item_count=len(telegram_out.items))
            )

    if max_age:
        filtered_batches: list[tuple[str, PaginatedListings]] = []
        for source, result in successful:
            items = _filter_listings_by_published_age(result.items, max_age)
            filtered_batches.append(
                (
                    source,
                    PaginatedListings(
                        items=items,
                        total=len(items),
                        page=result.page,
                        per_page=result.per_page,
                        pages=max((len(items) + result.per_page - 1) // result.per_page, 0),
                    ),
                )
            )
        successful = filtered_batches

    category = (filters.category or "all").strip().lower()
    if category in {"used", "new", "import"}:
        from app.services.search.category import listing_matches_category

        filtered_batches = []
        for source, result in successful:
            # AUTO.RIA «під пригон» уже відфільтрований параметром custom=1.
            if source == "auto_ria" and category == "import":
                filtered_batches.append((source, result))
                continue
            items = [item for item in result.items if listing_matches_category(item, category)]
            filtered_batches.append(
                (
                    source,
                    PaginatedListings(
                        items=items,
                        total=len(items),
                        page=result.page,
                        per_page=result.per_page,
                        pages=max((len(items) + result.per_page - 1) // result.per_page, 0),
                    ),
                )
            )
        successful = filtered_batches

    from app.services.search.advanced_filters import (
        advanced_filters_active,
        filter_listings_by_advanced,
    )

    if advanced_filters_active(filters):
        filtered_batches = []
        for source, result in successful:
            items = filter_listings_by_advanced(list(result.items), filters)
            filtered_batches.append(
                (
                    source,
                    PaginatedListings(
                        items=items,
                        total=len(items),
                        page=result.page,
                        per_page=result.per_page,
                        pages=max((len(items) + result.per_page - 1) // result.per_page, 0),
                    ),
                )
            )
        successful = filtered_batches

    from app.services.listings.duplicates import (
        collapse_listings_with_db_mirrors,
        mark_duplicates_in_pool,
    )

    page_items, nav_total, market_total = _merge_multi_source_page(
        successful,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
    )
    page_items = mark_duplicates_in_pool(page_items)

    if db is not None and page_items:
        page_items = await collapse_listings_with_db_mirrors(db, page_items)

    if not page_items:
        if errors and not successful:
            raise _pick_primary_error(errors)
        await _notify_partial_source_failures(source_statuses, filters)
        return SearchListingsOutcome(
            result=_empty_page(page, per_page),
            sources=source_statuses,
        )

    pages = (nav_total + per_page - 1) // per_page if nav_total else 1

    await _notify_partial_source_failures(source_statuses, filters)

    return SearchListingsOutcome(
        result=PaginatedListings(
            items=page_items,
            total=nav_total,
            market_total=market_total if market_total > nav_total else None,
            page=page,
            per_page=per_page,
            pages=pages,
        ),
        sources=source_statuses,
    )


async def search_listings(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    db=None,
) -> PaginatedListings:
    outcome = await search_listings_outcome(
        filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        use_cache=use_cache,
        cache_ttl_seconds=cache_ttl_seconds,
        db=db,
    )
    return outcome.result


# ---------------------------------------------------------------------------
# Slot-based pool builder — lazy AUTO.RIA hydration
# ---------------------------------------------------------------------------


def _filter_listings_by_brand_model(
    items: list[ListingOut],
    filters: SearchFilters,
) -> list[ListingOut]:
    if not ((filters.brand or "").strip() or (filters.model or "").strip()):
        return items
    from app.services.telegram_channels.mapper import listing_out_matches_filters

    return [item for item in items if listing_out_matches_filters(item, filters)]


def _listing_to_slot(item: ListingOut) -> dict:
    """ListingOut → slot для live-pool (AR — stub, OLX/Telegram — повний об'єкт)."""
    lid = item.id or ""
    src = (item.source or "").strip().lower()
    payload = item.model_dump(mode="json") if (item.alternate_sources or []) else None
    if src in ("auto_ria", "autoria", "auto.ria") or lid.startswith(("auto_ria_", "new_auto_ria_")):
        if lid.startswith("new_auto_ria_"):
            slot: dict = {"s": "n", "i": lid.removeprefix("new_auto_ria_")}
        else:
            slot = {"s": "r", "i": lid.removeprefix("auto_ria_")}
        if payload:
            slot["d"] = payload
        return slot
    if src == "telegram" or lid.startswith("telegram_"):
        return {"s": "t", "d": item.model_dump(mode="json")}
    if src == "imperiya" or lid.startswith("imperiya_"):
        return {"s": "i", "d": item.model_dump(mode="json")}
    return {"s": "o", "d": item.model_dump(mode="json")}


async def _build_globally_sorted_slots(
    *,
    auto_ria_ids: list[str],
    olx_items: list[ListingOut],
    telegram_items: list[ListingOut],
    limit: int,
    sort_by: str,
    filters: SearchFilters | None = None,
) -> list[dict]:
    """Глобальне сортування по даті/ціні тощо між усіма джерелами.

    AUTO.RIA IDs гідруємо (з Redis-кешем), щоб знати published_at, потім
    сортуємо разом з OLX/Telegram. У пул кладемо stubs у вже правильному порядку.
    """
    from app.services.listings.duplicates import dedupe_telegram_posts_in_pool, mark_duplicates_in_pool
    from app.services.search.pool_cache import (
        _batch_hydrate_auto_ria,
        _batch_hydrate_new_auto_ria,
    )

    # Достатньо для перших сторінок; решту AR допишемо в кінці в API-порядку.
    hydrate_cap = min(max(limit, 0), 200)
    used_ids = [aid for aid in auto_ria_ids if not aid.startswith("n:")][:hydrate_cap]
    new_budget = max(0, hydrate_cap - len(used_ids))
    new_ids = [aid[2:] for aid in auto_ria_ids if aid.startswith("n:")][:new_budget]

    try:
        hydrated_used, hydrated_new = await asyncio.wait_for(
            asyncio.gather(
                _batch_hydrate_auto_ria(used_ids),
                _batch_hydrate_new_auto_ria(new_ids),
            ),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        logger.warning("AR hydrate-for-sort timed out; falling back to interleave")
        return _build_interleaved_slots(
            auto_ria_ids=auto_ria_ids,
            olx_items=olx_items,
            telegram_items=telegram_items,
            limit=limit,
            sort_by=sort_by,
        )
    except Exception:
        logger.exception("AR hydrate-for-sort failed; falling back to interleave")
        return _build_interleaved_slots(
            auto_ria_ids=auto_ria_ids,
            olx_items=olx_items,
            telegram_items=telegram_items,
            limit=limit,
            sort_by=sort_by,
        )

    combined: list[ListingOut] = list(olx_items) + list(telegram_items)
    combined.extend(hydrated_used.values())
    combined.extend(hydrated_new.values())
    combined = dedupe_telegram_posts_in_pool(mark_duplicates_in_pool(combined))
    if filters is not None:
        combined = _filter_listings_by_brand_model(combined, filters)

    seen: set[str] = set()
    unique: list[ListingOut] = []
    for item in combined:
        if not item.id or item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)

    sorted_items = sort_listings(unique, sort_by)
    hydrated_raw = set(hydrated_used) | set(hydrated_new)

    slots: list[dict] = []
    for item in sorted_items:
        if len(slots) >= limit:
            break
        slots.append(_listing_to_slot(item))

    # AR без дати (гідрація не вдалась) — в кінець, у порядку API.
    for aid in auto_ria_ids:
        if len(slots) >= limit:
            break
        raw = aid[2:] if aid.startswith("n:") else aid
        if raw in hydrated_raw:
            continue
        if aid.startswith("n:"):
            slots.append({"s": "n", "i": raw})
        else:
            slots.append({"s": "r", "i": raw})

    return slots[:limit]


async def _build_vin_aware_slots(
    *,
    auto_ria_ids: list[str],
    ot_items: list[ListingOut],
    limit: int,
    sort_by: str,
) -> list[dict]:
    """Пул з VIN-dedup між AUTO.RIA та OLX/Telegram (канонічна картка — AUTO.RIA)."""
    from app.services.listings.duplicates import mark_duplicates_in_pool
    from app.services.search.pool_cache import (
        _batch_hydrate_auto_ria,
        _batch_hydrate_new_auto_ria,
    )

    hydrate_cap = min(max(limit, 0), 200)
    used_ids = [aid for aid in auto_ria_ids if not aid.startswith("n:")][:hydrate_cap]
    new_budget = max(0, hydrate_cap - len(used_ids))
    new_ids = [aid[2:] for aid in auto_ria_ids if aid.startswith("n:")][:new_budget]

    try:
        hydrated_used, hydrated_new = await asyncio.wait_for(
            asyncio.gather(
                _batch_hydrate_auto_ria(used_ids),
                _batch_hydrate_new_auto_ria(new_ids),
            ),
            timeout=45.0,
        )
    except (asyncio.TimeoutError, Exception):
        logger.warning("VIN-aware pool: AR hydrate failed, falling back to fair blend")
        olx_only = [i for i in ot_items if (i.source or "").lower() == "olx"]
        tg_only = [i for i in ot_items if (i.source or "").lower() == "telegram"]
        return _build_fair_blend_slots(
            auto_ria_ids=auto_ria_ids,
            olx_items=olx_only,
            telegram_items=tg_only,
            limit=limit,
            sort_by=sort_by,
        )

    ar_items = list(hydrated_used.values()) + list(hydrated_new.values())
    merged = mark_duplicates_in_pool([*ot_items, *ar_items])
    merged = sort_listings(merged, sort_by)

    slots: list[dict] = []
    represented_ar: set[str] = set()
    for item in merged:
        if len(slots) >= limit:
            break
        slots.append(_listing_to_slot(item))
        lid = item.id or ""
        if lid.startswith("new_auto_ria_"):
            represented_ar.add("n:" + lid.removeprefix("new_auto_ria_"))
        elif lid.startswith("auto_ria_"):
            represented_ar.add(lid.removeprefix("auto_ria_"))

    for aid in auto_ria_ids:
        if len(slots) >= limit:
            break
        if aid in represented_ar:
            continue
        if aid.startswith("n:"):
            slots.append({"s": "n", "i": aid[2:]})
        else:
            slots.append({"s": "r", "i": aid})

    return slots[:limit]


def _make_ar_slots(auto_ria_ids: list[str]) -> list[dict]:
    slots = []
    for aid in auto_ria_ids:
        if aid.startswith("n:"):
            slots.append({"s": "n", "i": aid[2:]})
        else:
            slots.append({"s": "r", "i": aid})
    return slots


def _slot_id(slot: dict) -> str:
    sid = slot.get("i") or (slot.get("d") or {}).get("id", "")
    return str(sid)


def _build_fair_blend_slots(
    *,
    auto_ria_ids: list[str],
    olx_items: list[ListingOut],
    telegram_items: list[ListingOut],
    imperiya_items: list[ListingOut] | None = None,
    limit: int,
    sort_by: str = "newest",
) -> list[dict]:
    """Round-robin OLX → Імперія → Telegram → AUTO.RIA; усередині кожного — sort_by."""
    imperiya_items = imperiya_items or []
    batches: list[tuple[str, list[dict]]] = []
    if olx_items:
        batches.append(
            (
                "olx",
                [_listing_to_slot(item) for item in sort_listings(olx_items, sort_by)],
            )
        )
    if imperiya_items:
        batches.append(
            (
                "imperiya",
                [_listing_to_slot(item) for item in sort_listings(imperiya_items, sort_by)],
            )
        )
    if telegram_items:
        batches.append(
            (
                "telegram",
                [_listing_to_slot(item) for item in sort_listings(telegram_items, sort_by)],
            )
        )
    if auto_ria_ids:
        batches.append(("auto_ria", _make_ar_slots(auto_ria_ids)))

    if not batches:
        return []
    if len(batches) == 1:
        return batches[0][1][:limit]

    batches = sorted(batches, key=lambda row: _SOURCE_BLEND_ORDER.get(row[0], 99))
    queues = {source: list(slots) for source, slots in batches}
    order = [source for source, _ in batches]
    merged: list[dict] = []
    seen_ids: set[str] = set()

    while len(merged) < limit:
        added = False
        for source in order:
            if len(merged) >= limit:
                break
            queue = queues[source]
            while queue:
                candidate = queue.pop(0)
                sid = _slot_id(candidate)
                if sid and sid in seen_ids:
                    continue
                if sid:
                    seen_ids.add(sid)
                merged.append(candidate)
                added = True
                break
        if not added:
            break

    return merged


def _build_interleaved_slots(
    *,
    auto_ria_ids: list[str],
    olx_items: list[ListingOut],
    telegram_items: list[ListingOut],
    limit: int,
    sort_by: str = "newest",
    imperiya_items: list[ListingOut] | None = None,
) -> list[dict]:
    """Fallback: fair round-robin між джерелами (коли гідрація AR недоступна)."""
    return _build_fair_blend_slots(
        auto_ria_ids=auto_ria_ids,
        olx_items=olx_items,
        telegram_items=telegram_items,
        imperiya_items=imperiya_items,
        limit=limit,
        sort_by=sort_by,
    )


async def build_live_search_pool(
    filters: SearchFilters,
    *,
    sort_by: str,
    max_ids: int = SOURCE_POOL_CAP,
    keyword_refresh: bool = False,
    olx_enrich_details: bool = True,
    db=None,
) -> tuple[list[dict], int, int, list[SourceSearchStatus]]:
    """Build a slot-based live search pool.

    AUTO.RIA: collect IDs only (fast, no get_info calls).
    OLX/Telegram: fetch full listings as usual.
    Returns (slots, nav_total, market_total, source_statuses).
    """
    from app.services.search.brand_model_keywords import normalize_search_filters

    filters = normalize_search_filters(filters)
    from app.services.auto_ria.service import collect_auto_ria_ids
    from app.services.search.pool_cache import LIVE_POOL_SIZE as POOL_LIMIT, filter_auto_ria_ids_by_filters

    sources = normalize_sources(filters.sources)
    source_statuses: list[SourceSearchStatus] = []
    errors: list[Exception] = []

    auto_ria_ids: list[str] = []
    auto_ria_market_total = 0
    olx_result = _empty_page(1, max_ids)
    imperiya_result = _empty_page(1, max_ids)
    telegram_result = _empty_page(1, max_ids)
    olx_error: str | None = None

    async def run_auto_ria():
        try:
            return await asyncio.wait_for(
                collect_auto_ria_ids(filters, max_ids=max_ids, sort_by=sort_by),
                timeout=AUTO_RIA_POOL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return [], 0
        except AutoRiaError as exc:
            raise
        except Exception as exc:
            logger.warning("AUTO.RIA ID collect failed: %s", exc)
            return [], 0

    async def run_olx():
        try:
            async with acquire_olx_slot():
                result = await asyncio.wait_for(
                    _search_olx_body(
                        filters,
                        page=1,
                        per_page=max_ids,
                        sort_by=sort_by,
                        enrich_details=olx_enrich_details,
                        use_cache=True,
                        cache_ttl_seconds=120,
                    ),
                    timeout=OLX_SEARCH_TIMEOUT_SECONDS,
                )
            return result, None
        except asyncio.TimeoutError:
            return _empty_page(1, max_ids), f"таймаут {OLX_SEARCH_TIMEOUT_SECONDS:.0f}s"
        except OlxError as exc:
            return _empty_page(1, max_ids), str(exc)
        except Exception as exc:
            return _empty_page(1, max_ids), str(exc)

    async def run_imperiya():
        try:
            return await asyncio.wait_for(
                _fetch_source_pool(
                    "imperiya",
                    filters,
                    need=max_ids,
                    sort_by=sort_by,
                    keyword_refresh=keyword_refresh,
                ),
                timeout=IMPERIYA_POOL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return _empty_page(1, max_ids)
        except Exception as exc:
            logger.warning("Імперія Авто pool fetch failed: %s", exc)
            return _empty_page(1, max_ids)

    async def run_telegram():
        try:
            return await asyncio.wait_for(
                _fetch_source_pool(
                    "telegram",
                    filters,
                    need=TELEGRAM_POOL_CAP,
                    sort_by=sort_by,
                    keyword_refresh=keyword_refresh,
                    db=db,
                ),
                timeout=TELEGRAM_POOL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return _empty_page(1, TELEGRAM_POOL_CAP)
        except Exception as exc:
            logger.warning("Telegram pool fetch failed: %s", exc)
            return _empty_page(1, TELEGRAM_POOL_CAP)

    tasks: list = []
    task_order: list[str] = []
    if "auto_ria" in sources:
        tasks.append(asyncio.create_task(run_auto_ria()))
        task_order.append("auto_ria")
    if "olx" in sources:
        tasks.append(asyncio.create_task(run_olx()))
        task_order.append("olx")
    if "imperiya" in sources:
        tasks.append(asyncio.create_task(run_imperiya()))
        task_order.append("imperiya")
    if "telegram" in sources:
        tasks.append(asyncio.create_task(run_telegram()))
        task_order.append("telegram")

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    result_index = 0
    if "auto_ria" in task_order:
        res = raw_results[result_index]
        result_index += 1
        if isinstance(res, BaseException):
            errors.append(res)
            source_statuses.append(SourceSearchStatus(source="AUTO.RIA", item_count=0, error=str(res)))
        else:
            auto_ria_ids, auto_ria_market_total = res
            source_statuses.append(SourceSearchStatus(source="AUTO.RIA", item_count=len(auto_ria_ids)))

    if "olx" in task_order:
        res = raw_results[result_index]
        result_index += 1
        if isinstance(res, BaseException):
            olx_result = _empty_page(1, max_ids)
            olx_error = str(res)
        else:
            olx_result, olx_error = res
        source_statuses.append(
            SourceSearchStatus(source="OLX", item_count=len(olx_result.items), error=olx_error)
        )

    if "imperiya" in task_order:
        res = raw_results[result_index]
        result_index += 1
        if isinstance(res, BaseException):
            imperiya_result = _empty_page(1, max_ids)
            source_statuses.append(
                SourceSearchStatus(source="Імперія Авто", item_count=0, error=str(res))
            )
        else:
            imperiya_result = res
            source_statuses.append(
                SourceSearchStatus(source="Імперія Авто", item_count=len(imperiya_result.items))
            )

    if "telegram" in task_order:
        res = raw_results[result_index]
        if isinstance(res, BaseException):
            telegram_result = _empty_page(1, TELEGRAM_POOL_CAP)
        else:
            telegram_result = res
        source_statuses.append(
            SourceSearchStatus(source="Telegram", item_count=len(telegram_result.items))
        )

    # Raise if AUTO.RIA failed and it was the only source
    if errors and "auto_ria" in sources and len(sources) == 1:
        raise _pick_primary_error(errors)

    from app.services.auto_ria.catalog import model_filter_needs_post_filter
    from app.services.auto_ria.client import AutoRiaClient
    from app.services.listings.duplicates import dedupe_telegram_posts_in_pool, mark_duplicates_in_pool

    from app.services.search.advanced_filters import filter_listings_by_advanced

    brand_model_filter = bool((filters.brand or "").strip() or (filters.model or "").strip())
    model_post_filter = False
    if brand_model_filter and (filters.model or "").strip():
        try:
            model_post_filter = await model_filter_needs_post_filter(AutoRiaClient(), filters)
        except Exception:
            logger.exception("model_post_filter check failed in pool build")

    if model_post_filter and auto_ria_ids:
        auto_ria_ids = await filter_auto_ria_ids_by_filters(auto_ria_ids, filters)

    olx_filtered = _filter_listings_by_brand_model(list(olx_result.items), filters)
    imperiya_filtered = _filter_listings_by_brand_model(list(imperiya_result.items), filters)
    telegram_filtered = _filter_listings_by_brand_model(list(telegram_result.items), filters)

    # VIN-дублі між OLX / Імперія / Telegram — в одному пулі.
    ot_merged = mark_duplicates_in_pool(
        dedupe_telegram_posts_in_pool(
            sort_listings(
                list(olx_filtered) + list(imperiya_filtered) + list(telegram_filtered),
                sort_by,
            ),
        ),
    )
    ot_merged = filter_listings_by_advanced(ot_merged, filters)
    olx_sorted = [item for item in ot_merged if (item.source or "").lower() == "olx"]
    imperiya_sorted = [item for item in ot_merged if (item.source or "").lower() == "imperiya"]
    telegram_sorted = [item for item in ot_merged if (item.source or "").lower() == "telegram"]

    if auto_ria_ids and (olx_sorted or imperiya_sorted or telegram_sorted):
        slots = await _build_vin_aware_slots(
            auto_ria_ids=auto_ria_ids,
            ot_items=ot_merged,
            limit=POOL_LIMIT,
            sort_by=sort_by,
        )
    elif auto_ria_ids and sort_by in ("newest", "published_desc"):
        # Лише AUTO.RIA + newest: API вже віддав IDs від нових до старих (order_by=7).
        slots = _make_ar_slots(auto_ria_ids)[:POOL_LIMIT]
    elif auto_ria_ids:
        slots = await _build_globally_sorted_slots(
            auto_ria_ids=auto_ria_ids,
            olx_items=[],
            telegram_items=[],
            limit=POOL_LIMIT,
            sort_by=sort_by,
            filters=filters,
        )
    else:
        slots = _build_interleaved_slots(
            auto_ria_ids=[],
            olx_items=olx_sorted,
            telegram_items=telegram_sorted,
            imperiya_items=imperiya_sorted,
            limit=POOL_LIMIT,
            sort_by=sort_by,
        )

    nav_total = len(slots)
    if brand_model_filter:
        market_total = nav_total
    else:
        market_total = (
            auto_ria_market_total
            + olx_result.total
            + imperiya_result.total
            + telegram_result.total
        )

    if brand_model_filter:
        source_statuses = [
            SourceSearchStatus(
                source=row.source,
                item_count=(
                    len(olx_sorted)
                    if row.source == "OLX"
                    else len(imperiya_sorted)
                    if row.source == "Імперія Авто"
                    else len(telegram_sorted)
                    if row.source == "Telegram"
                    else len(auto_ria_ids)
                    if row.source == "AUTO.RIA"
                    else row.item_count
                ),
                error=row.error,
            )
            for row in source_statuses
        ]

    await _notify_partial_source_failures(source_statuses, filters)

    return slots, nav_total, market_total, source_statuses
