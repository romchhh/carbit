from __future__ import annotations

import asyncio
import json

from app.schemas.schemas import ListingOut, PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
from app.services.auto_ria.mapper import (
    filters_to_search_params,
    info_to_listing,
    new_info_to_listing,
    sort_listings,
)
from app.services.search.concurrency import acquire_auto_ria_slot


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_auto_ria_uncached(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    async with acquire_auto_ria_slot():
        return await _search_auto_ria_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )


async def _search_auto_ria_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    client = AutoRiaClient()

    try:
        params = await filters_to_search_params(client, filters, page=page, per_page=per_page)
        search_data = await client.search(params)
    except ValueError as exc:
        raise AutoRiaError(str(exc)) from exc

    search_result = (search_data.get("result") or {}).get("search_result") or {}
    total = int(search_result.get("count") or 0)
    raw_ids = search_result.get("ids") or []
    auto_ids = [str(item) for item in raw_ids if item][: max(per_page, 0)]

    sem = asyncio.Semaphore(10)

    async def fetch_one(auto_id: str) -> ListingOut | None:
        async with sem:
            try:
                info = await client.get_info(auto_id)
                return info_to_listing(info, fotos=None)
            except AutoRiaError:
                return None

    # Для категорії "all" паралельно тягнемо також нові авто від дилерів (/auto/new/search)
    category = (filters.category or "all").strip().lower()
    new_car_task = None
    new_total = 0
    if category == "all" and page == 1:
        new_params = _build_new_search_params(params)
        new_cap = max(min(per_page // 2, 50), 20)
        new_params.update({"page": 1, "limit": new_cap})

        async def _fetch_new_cars() -> list[ListingOut]:
            nonlocal new_total
            try:
                async with acquire_auto_ria_slot():
                    new_data = await client.search_new(new_params)
                new_total = int(new_data.get("count") or 0)
                new_ids = [str(rid) for rid in (new_data.get("autos") or []) if rid][:new_cap]

                async def fetch_new_one(aid: str) -> ListingOut | None:
                    async with sem:
                        try:
                            info = await client.get_new_info(aid)
                            return new_info_to_listing(info)
                        except Exception:
                            return None

                return [item for item in await asyncio.gather(*(fetch_new_one(aid) for aid in new_ids)) if item]
            except Exception:
                return []

        new_car_task = asyncio.create_task(_fetch_new_cars())

    listings = [item for item in await asyncio.gather(*(fetch_one(aid) for aid in auto_ids)) if item]

    if new_car_task is not None:
        new_listings = await new_car_task
        # Deduplicate by ID before combining
        seen = {lst.id for lst in listings}
        for lst in new_listings:
            if lst.id not in seen:
                listings.append(lst)
                seen.add(lst.id)
        total += new_total

    listings = sort_listings(listings, sort_by)

    pages = (total + per_page - 1) // per_page if total else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def _collect_ids_raw(
    client: AutoRiaClient,
    base_params: dict,
    *,
    max_ids: int,
) -> tuple[list[str], int]:
    """Paginate AUTO.RIA search with given params, return (ids, api_total). No get_info calls."""
    all_ids: list[str] = []
    total = 0
    api_page = 0

    while len(all_ids) < max_ids:
        params = {**base_params, "page": api_page, "countpage": 50}
        async with acquire_auto_ria_slot():
            data = await client.search(params)

        search_result = ((data.get("result") or {}).get("search_result")) or {}
        if api_page == 0:
            total = int(search_result.get("count") or 0)

        raw_ids = search_result.get("ids") or []
        if not raw_ids:
            break

        for rid in raw_ids:
            if rid and len(all_ids) < max_ids:
                all_ids.append(str(rid))

        if len(raw_ids) < 50 or len(all_ids) >= total:
            break
        api_page += 1

    return all_ids, total


def _build_new_search_params(base_params: dict) -> dict:
    """Конвертує resolved параметри вживаних авто у формат /auto/new/search.

    Каталог марок/моделей у AUTO.RIA спільний — ті самі markaId/modelId.
    """
    params: dict = {}
    if "marka_id[0]" in base_params:
        params["markaId"] = base_params["marka_id[0]"]
    mid = base_params.get("model_id[0]")
    if mid:
        params["modelId"] = mid
    if "state[0]" in base_params:
        params["stateId"] = base_params["state[0]"]
    cid = base_params.get("city[0]")
    if cid:
        params["cityId"] = cid
    if "currency" in base_params:
        params["currencyId"] = base_params["currency"]
    if "price_ot" in base_params:
        params["priceFrom"] = base_params["price_ot"]
    if "price_do" in base_params:
        params["priceTo"] = base_params["price_do"]
    if "s_yers[0]" in base_params:
        params["yearFrom"] = base_params["s_yers[0]"]
    if "po_yers[0]" in base_params:
        params["yearTo"] = base_params["po_yers[0]"]
    return params


async def _collect_new_ids_raw(
    client: AutoRiaClient,
    new_params: dict,
    *,
    max_ids: int,
) -> tuple[list[str], int]:
    """Paginate /auto/new/search (1-indexed, limit ≤ 50). Returns (ids, api_total)."""
    all_ids: list[str] = []
    total = 0
    api_page = 1

    while len(all_ids) < max_ids:
        params = {**new_params, "page": api_page, "limit": 50}
        async with acquire_auto_ria_slot():
            data = await client.search_new(params)

        if api_page == 1:
            total = int(data.get("count") or 0)

        raw_ids = data.get("autos") or []
        if not raw_ids:
            break

        for rid in raw_ids:
            if rid and len(all_ids) < max_ids:
                all_ids.append(str(rid))

        if len(raw_ids) < 50 or len(all_ids) >= total:
            break
        api_page += 1

    return all_ids, total


def _interleave_two(a: list[str], b: list[str]) -> list[str]:
    """Alternate items from two lists: a[0], b[0], a[1], b[1], ..."""
    result: list[str] = []
    ia, ib = iter(a), iter(b)
    sentinel = object()
    while True:
        va = next(ia, sentinel)
        vb = next(ib, sentinel)
        if va is sentinel and vb is sentinel:
            break
        if va is not sentinel:
            result.append(va)  # type: ignore[arg-type]
        if vb is not sentinel:
            result.append(vb)  # type: ignore[arg-type]
    return result


async def collect_auto_ria_ids(
    filters: SearchFilters,
    *,
    max_ids: int = 500,
) -> tuple[list[str], int]:
    """Collect AUTO.RIA listing IDs without hydrating details. Much faster than full search.

    For "all" category: two parallel searches — used (searchType=4) + new/dealer (searchType=1).
    Returns (ids, api_total_combined).
    """
    client = AutoRiaClient()
    try:
        base_params = await filters_to_search_params(client, filters, page=1, per_page=50)
    except ValueError as exc:
        raise AutoRiaError(str(exc)) from exc

    category = (filters.category or "all").strip().lower()

    if category == "all":
        # Два паралельних запити:
        #   1. /auto/search (searchType=4) — вживані/приватні
        #   2. /auto/new/search — нові авто від дилерів (справжній окремий endpoint)
        half = max(max_ids // 2, 50)
        new_params = _build_new_search_params(base_params)

        (used_ids, used_total), (new_ids, new_total) = await asyncio.gather(
            _collect_ids_raw(client, base_params, max_ids=half),
            _collect_new_ids_raw(client, new_params, max_ids=half),
        )

        # Нові авто позначаємо префіксом "n:" — щоб пул-кеш знав який endpoint використовувати
        tagged_new_ids = [f"n:{aid}" for aid in new_ids]

        seen: set[str] = set()
        combined: list[str] = []
        for aid in _interleave_two(tagged_new_ids, used_ids):
            if aid not in seen:
                seen.add(aid)
                combined.append(aid)
                if len(combined) >= max_ids:
                    break

        return combined, used_total + new_total
    else:
        # Category-specific: mapper already set correct searchType/custom
        return await _collect_ids_raw(client, base_params, max_ids=max_ids)


async def hydrate_auto_ria_ids(
    ids: list[str],
    *,
    sort_by: str = "newest",
) -> list[ListingOut]:
    """Hydrate a list of AUTO.RIA IDs → full ListingOut objects (for on-demand page hydration)."""
    if not ids:
        return []
    client = AutoRiaClient()
    sem = asyncio.Semaphore(10)

    async def fetch_one(auto_id: str) -> ListingOut | None:
        async with sem:
            try:
                info = await client.get_info(auto_id)
                return info_to_listing(info, fotos=None)
            except AutoRiaError:
                return None

    listings = [item for item in await asyncio.gather(*(fetch_one(aid) for aid in ids)) if item]
    return sort_listings(listings, sort_by)


async def search_auto_ria(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
) -> PaginatedListings:
    if not use_cache:
        return await _search_auto_ria_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )

    key = _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by)
    is_browse = not filters.model_dump(exclude_none=True)
    ttl = 180 if is_browse else cache_ttl_seconds
    return await get_or_fetch(
        key,
        lambda: _search_auto_ria_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        ),
        ttl_seconds=ttl,
    )
