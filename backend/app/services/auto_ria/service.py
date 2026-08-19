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


def _new_search_ids(data: dict) -> list[str]:
    """AUTO.RIA /auto/new/search віддає `ids`; старі приклади в документації мали `autos`."""
    raw = data.get("ids")
    if not raw:
        raw = data.get("autos") or []
    return [str(rid) for rid in raw if rid]


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
    except ValueError as exc:
        raise AutoRiaError(str(exc)) from exc

    category = (filters.category or "all").strip().lower()

    try:
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

    # Для «всі» і «нові» паралельно тягнемо дилерські авто (/auto/new/search)
    new_car_task = None
    new_total = 0
    if category in ("all", "new") and page == 1:
        new_cap = max(min(per_page // 2, 50), 20)

        async def _fetch_new_cars() -> list[ListingOut]:
            nonlocal new_total
            try:
                new_ids, new_total = await _collect_new_ids_expanded(
                    client, params, filters, max_ids=new_cap, use_slot=False
                )

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

    from app.services.telegram_channels.mapper import listing_out_matches_filters

    listings = [item for item in listings if listing_out_matches_filters(item, filters)]

    pages = (total + per_page - 1) // per_page if total else 0
    return PaginatedListings(
        items=listings,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def _search_new_auto_ria_only(
    client: AutoRiaClient,
    used_params: dict,
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
) -> PaginatedListings:
    """Лише GET /auto/new/search + /auto/new/auto/{id} — без /auto/search."""
    offset = (max(page, 1) - 1) * max(per_page, 1)
    need = offset + max(per_page, 0)
    all_ids, total = await _collect_new_ids_expanded(
        client, used_params, filters, max_ids=max(need, 1), use_slot=False
    )
    auto_ids = all_ids[offset : offset + max(per_page, 0)]

    sem = asyncio.Semaphore(10)

    async def fetch_one(auto_id: str) -> ListingOut | None:
        async with sem:
            try:
                info = await client.get_new_info(auto_id)
                return new_info_to_listing(info)
            except Exception:
                return None

    listings = [item for item in await asyncio.gather(*(fetch_one(aid) for aid in auto_ids)) if item]
    listings = sort_listings(listings, sort_by)

    from app.services.telegram_channels.mapper import listing_out_matches_filters

    listings = [item for item in listings if listing_out_matches_filters(item, filters)]
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
    sort_by: str = "newest",
) -> tuple[list[str], int]:
    """Paginate AUTO.RIA search with given params, return (ids, api_total). No get_info calls."""
    all_ids: list[str] = []
    total = 0
    api_page = 0

    # order_by=7 → date_desc (найновіші); 8 = date_asc (найстаріші). НЕ плутати.
    if sort_by in ("newest", "published_desc"):
        sort_patch: dict = {"order_by": 7}
    elif sort_by == "published_asc":
        sort_patch = {"order_by": 8}
    else:
        sort_patch = {}

    while len(all_ids) < max_ids:
        params = {**base_params, **sort_patch, "page": api_page, "countpage": 50}
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
    use_slot: bool = True,
) -> tuple[list[str], int]:
    """Paginate /auto/new/search (1-indexed, limit ≤ 50). Returns (ids, api_total)."""
    all_ids: list[str] = []
    total = 0
    api_page = 1

    while len(all_ids) < max_ids:
        params = {**new_params, "page": api_page, "limit": 50}
        if use_slot:
            async with acquire_auto_ria_slot():
                data = await client.search_new(params)
        else:
            data = await client.search_new(params)

        if api_page == 1:
            total = int(data.get("count") or 0)

        raw_ids = _new_search_ids(data)
        if not raw_ids:
            break

        for rid in raw_ids:
            if rid and len(all_ids) < max_ids:
                all_ids.append(str(rid))

        if len(raw_ids) < 50 or len(all_ids) >= total:
            break
        api_page += 1

    return all_ids, total


async def _new_model_ids_for_search(
    client: AutoRiaClient,
    used_params: dict,
    filters: SearchFilters,
) -> list[int]:
    """modelId з params + successor IDs для нових авто (A4→A5)."""
    primary: list[int] = []
    raw = used_params.get("model_id[0]")
    if raw:
        try:
            mid = int(raw)
        except (TypeError, ValueError):
            mid = 0
        if mid:
            primary.append(mid)
    if not ((filters.brand or "").strip() and (filters.model or "").strip()):
        return primary
    try:
        from app.services.auto_ria.catalog import resolve_new_search_model_ids

        extra = await resolve_new_search_model_ids(
            client, filters.brand or "", filters.model or ""
        )
    except Exception:
        extra = []
    if not extra:
        return primary
    seen = set(primary)
    out = list(primary)
    for mid in extra:
        if mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


async def _collect_new_ids_expanded(
    client: AutoRiaClient,
    used_params: dict,
    filters: SearchFilters,
    *,
    max_ids: int,
    use_slot: bool = True,
) -> tuple[list[str], int]:
    new_params = _build_new_search_params(used_params)
    model_ids = await _new_model_ids_for_search(client, used_params, filters)
    if len(model_ids) <= 1:
        if model_ids:
            new_params["modelId"] = model_ids[0]
        return await _collect_new_ids_raw(
            client, new_params, max_ids=max_ids, use_slot=use_slot
        )

    new_params.pop("modelId", None)
    parts = await asyncio.gather(
        *[
            _collect_new_ids_raw(
                client,
                {**new_params, "modelId": mid},
                max_ids=max_ids,
                use_slot=use_slot,
            )
            for mid in model_ids
        ]
    )
    seen: set[str] = set()
    ids: list[str] = []
    total = 0
    for part_ids, part_total in parts:
        total += int(part_total or 0)
        for aid in part_ids:
            if aid in seen:
                continue
            seen.add(aid)
            ids.append(aid)
            if len(ids) >= max_ids:
                return ids, total
    return ids, total


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
    sort_by: str = "newest",
) -> tuple[list[str], int]:
    """Collect AUTO.RIA listing IDs without hydrating details. Much faster than full search.

    For "new": used /auto/search (≤1000 км, будь-який рік) + /auto/new/search.
    For "all": used /auto/search + new /auto/new/search interleaved.
    """
    client = AutoRiaClient()
    try:
        base_params = await filters_to_search_params(client, filters, page=1, per_page=50)
    except ValueError as exc:
        raise AutoRiaError(str(exc)) from exc

    sort_oldest = sort_by == "published_asc"
    category = (filters.category or "all").strip().lower()

    if category in {"new", "all"}:
        # Два паралельних запити:
        #   1. /auto/search — для «new» уже raceTo=1 (≤1000 км, без підлоги року)
        #   2. /auto/new/search — нові авто від дилерів
        half = max(max_ids // 2, 50)

        (used_ids, used_total), (new_ids, new_total) = await asyncio.gather(
            _collect_ids_raw(client, base_params, max_ids=half, sort_by=sort_by),
            _collect_new_ids_expanded(client, base_params, filters, max_ids=half),
        )

        tagged_new_ids = [f"n:{aid}" for aid in new_ids]

        seen: set[str] = set()
        combined: list[str] = []
        if sort_oldest:
            stream = _interleave_two(used_ids, tagged_new_ids)
        else:
            stream = _interleave_two(tagged_new_ids, used_ids)
        for aid in stream:
            if aid not in seen:
                seen.add(aid)
                combined.append(aid)
                if len(combined) >= max_ids:
                    break

        return combined, used_total + new_total
    else:
        # Category-specific: mapper already set correct searchType/custom
        return await _collect_ids_raw(client, base_params, max_ids=max_ids, sort_by=sort_by)


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
