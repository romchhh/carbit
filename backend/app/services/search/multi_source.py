from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.mapper import sort_listings
from app.services.auto_ria.service import search_auto_ria
from app.services.olx.errors import OlxError
from app.services.olx.service import search_olx
from app.services.telegram_channels.ingest import search_telegram_listings

IMPLEMENTED_SOURCES = {"auto_ria", "olx", "telegram"}
OLX_SEARCH_TIMEOUT_SECONDS = 45.0


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
    per_page: int,
) -> list[ListingOut]:
    if not batches:
        return []

    if len(batches) == 1:
        return batches[0][1][:per_page]

    queues = {source: list(items) for source, items in batches}
    order = [source for source, _ in batches]
    merged: list[ListingOut] = []
    seen_ids: set[str] = set()

    while len(merged) < per_page:
        added = False
        for source in order:
            if len(merged) >= per_page:
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
    merged_items: list[ListingOut] = []
    total = 0

    for _, result in batches:
        merged_items.extend(result.items)
        total += result.total

    merged_items = sort_listings(merged_items, sort_by)
    start = (page - 1) * per_page
    end = start + per_page
    return merged_items[start:end], max(total, len(merged_items))


async def _search_single_source(
    source: str,
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
    use_cache: bool = True,
    db=None,
) -> PaginatedListings:
    if source == "telegram":
        if db is not None:
            return await search_telegram_listings(
                db,
                filters,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
            )
        async with AsyncSessionLocal() as session:
            return await search_telegram_listings(
                session,
                filters,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
            )
    if source == "olx":
        return await search_olx(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            use_cache=use_cache,
        )
    return await search_auto_ria(
        filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        use_cache=use_cache,
    )


async def _search_olx_safe(
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
    use_cache: bool = True,
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


async def search_listings_outcome(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "price_asc",
    use_cache: bool = True,
    db=None,
) -> SearchListingsOutcome:
    sources = normalize_sources(filters.sources)
    source_statuses: list[SourceSearchStatus] = []

    if len(sources) == 1:
        source = sources[0]
        try:
            result = await _search_single_source(
                source,
                filters,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                use_cache=use_cache,
                db=db,
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

    per_source_fetch = per_page if page == 1 else per_page * page
    errors: list[Exception] = []
    successful: list[tuple[str, PaginatedListings]] = []

    async def run_auto_ria() -> PaginatedListings | Exception:
        try:
            return await _search_single_source(
                "auto_ria",
                filters,
                page=1,
                per_page=per_source_fetch,
                sort_by=sort_by,
                use_cache=use_cache,
            )
        except Exception as exc:
            return exc

    async def run_olx() -> tuple[PaginatedListings, str | None]:
        return await _search_olx_safe(
            filters,
            page=1,
            per_page=per_source_fetch,
            sort_by=sort_by,
            use_cache=use_cache,
        )

    async def run_telegram() -> PaginatedListings | Exception:
        try:
            return await _search_single_source(
                "telegram",
                filters,
                page=1,
                per_page=per_source_fetch,
                sort_by=sort_by,
                db=db,
            )
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

    if page == 1:
        sorted_batches = [
            (source, sort_listings(list(result.items), sort_by))
            for source, result in successful
            if result.items
        ]
        page_items = _interleave_by_source(sorted_batches, per_page=per_page)
        total = sum(result.total for _, result in successful)
    else:
        page_items, total = _sorted_merge_slice(
            successful,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )

    if not page_items:
        if errors and not successful:
            raise _pick_primary_error(errors)
        return SearchListingsOutcome(
            result=_empty_page(page, per_page),
            sources=source_statuses,
        )

    pages = (total + per_page - 1) // per_page if total else 1

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
    sort_by: str = "price_asc",
    use_cache: bool = True,
) -> PaginatedListings:
    outcome = await search_listings_outcome(
        filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        use_cache=use_cache,
    )
    return outcome.result
