from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.mapper import sort_listings
from app.services.auto_ria.service import search_auto_ria
from app.services.olx.errors import OlxError
from app.services.olx.service import search_olx
from app.services.telegram.admin_alerts import notify_admin_parsing_error
from app.services.telegram_channels.ingest import search_telegram_listings

IMPLEMENTED_SOURCES = {"auto_ria", "olx", "telegram"}
OLX_SEARCH_TIMEOUT_SECONDS = 22.0
# Скільки оголошень тягнути з кожного джерела в спільний пул (режим «Шукати всі»).
# Більший пул + fair interleave → помітна частка OLX/Telegram, не лише AUTO.RIA.
SOURCE_POOL_CAP = 120
TELEGRAM_POOL_CAP = 240
TELEGRAM_MAX_SCAN = 1500
AUTO_RIA_PAGE_SIZE = 50
AUTO_RIA_POOL_TIMEOUT_SECONDS = 40.0
TELEGRAM_POOL_TIMEOUT_SECONDS = 25.0
# У змішаній видачі спочатку OLX/Telegram, щоб перші картки не були лише з AUTO.RIA.
_SOURCE_BLEND_ORDER = {"olx": 0, "telegram": 1, "auto_ria": 2}


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
    default = ["auto_ria", "olx"]
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
) -> tuple[list[ListingOut], int]:
    """Зливає джерела: сортує всередині кожного, далі fair interleave (не global sort)."""
    prepared: list[tuple[str, list[ListingOut]]] = []
    source_totals = 0

    for source, result in batches:
        source_totals += result.total
        items = sort_listings(list(result.items), sort_by)
        if items:
            prepared.append((source, items))

    prepared.sort(key=lambda pair: _SOURCE_BLEND_ORDER.get(pair[0], 99))

    # Повний змішаний пул (до page*per_page), щоб пагінація лишалась збалансованою.
    pool_limit = max(page, 1) * per_page
    available = sum(len(items) for _, items in prepared)
    merged_items = _interleave_by_source(prepared, limit=min(pool_limit, available))

    start = (page - 1) * per_page
    end = start + per_page
    page_items = merged_items[start:end]
    pool_size = len(merged_items)
    # Не завищуємо total вище того, що реально є в пулі для поточної видачі,
    # інакше «Показати ще» крутиться в порожнечу.
    if page_items and len(page_items) < per_page:
        total = start + len(page_items)
    else:
        total = max(source_totals, pool_size)
        if start + per_page >= pool_size:
            total = pool_size
    return page_items, total


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
        return await search_olx(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            use_cache=use_cache,
            cache_ttl_seconds=cache_ttl_seconds,
            enrich_details=olx_enrich_details,
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
    need = max(need, 1)
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
    """OLX не повинен ламати весь пошук — таймаут/помилки дають порожню видачу."""
    try:
        result = await asyncio.wait_for(
            search_olx(
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
        await notify_admin_parsing_error(
            source=status.source,
            error=status.error or "невідома помилка",
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
    sources = normalize_sources(filters.sources)
    source_statuses: list[SourceSearchStatus] = []
    max_age = _published_max_age(filters)

    if len(sources) == 1:
        source = sources[0]
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
            result = await asyncio.wait_for(
                _fetch_source_pool(
                    "olx",
                    filters,
                    need=pool_need,
                    sort_by=sort_by,
                    use_cache=use_cache,
                    cache_ttl_seconds=cache_ttl_seconds,
                    keyword_refresh=keyword_refresh,
                    olx_enrich_details=olx_enrich_details,
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

    page_items, total = _sorted_merge_slice(
        successful,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
    )

    if not page_items:
        if errors and not successful:
            raise _pick_primary_error(errors)
        await _notify_partial_source_failures(source_statuses, filters)
        return SearchListingsOutcome(
            result=_empty_page(page, per_page),
            sources=source_statuses,
        )

    pages = (total + per_page - 1) // per_page if total else 1

    await _notify_partial_source_failures(source_statuses, filters)

    return SearchListingsOutcome(
        result=PaginatedListings(
            items=page_items,
            total=total,
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
