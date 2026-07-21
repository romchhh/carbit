from __future__ import annotations

import asyncio
import json
import random

import copy

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.olx.brand_slugs import (
    brand_model_forces_text_search,
    brand_uses_olx_text_search,
    compose_olx_text_query,
)
from app.services.olx.client import OlxClient
from app.services.olx.constants import MAX_DELAY, MIN_DELAY, OFFERS_API_LIMIT
from app.services.olx.mapper import filters_to_olx_params, olx_listing_to_listing_out
from app.services.olx.parser import (
    OlxListing,
    OlxSearchParams,
    apply_details_to_listing,
    build_search_url,
    has_next_page,
    html_looks_like_results_page,
    listing_needs_enrichment,
    parse_listing_page,
    passes_olx_filters,
)
from app.services.olx.errors import OlxError
from app.services.search.concurrency import acquire_olx_slot
from app.services.telegram.admin_alerts import notify_admin_parsing_error


def _switch_params_to_text_query(params: OlxSearchParams, filters: SearchFilters) -> OlxSearchParams:
    """Fallback, коли /brand/model/ на OLX дає 404 → /q-{brand}/ або /q-mersedes-gla/."""
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if not brand and not model:
        return params
    query = compose_olx_text_query(brand, model)
    if query:
        params.text_query = query
    elif brand:
        params.text_query = brand
    elif model:
        params.text_query = model
    if brand:
        params.brand_label = brand
    if model:
        params.model_label = model
    params.brand = None
    params.model = None
    return params


def _olx_text_query(filters: SearchFilters, params: OlxSearchParams) -> str | None:
    """Один текстовий запит для /q-/ пошуку. OLX сам розуміє варіанти написань."""
    if not params.text_query:
        return None
    return params.text_query


def _listing_dedupe_key(listing: OlxListing) -> str:
    if listing.listing_id:
        return f"id:{listing.listing_id}"
    if listing.url:
        return f"url:{listing.url.split('?', 1)[0].rstrip('/')}"
    return f"title:{(listing.title or '').strip().lower()}"


def _olx_collect_target(*, page: int, per_page: int, needs_post_filter: bool, has_text_query: bool = False) -> int:
    """Скільки оголошень потрібно зібрати з OLX перед пост-фільтром."""
    end = max(page, 1) * per_page
    if has_text_query:
        # text_query відсікає частину — збираємо 2× запас (не більше, щоб не таймаутити)
        return end + max(per_page * 2, 40)
    if needs_post_filter:
        return end + max(per_page, 20)
    return end + max(per_page // 2, 8)


def _olx_max_scan_pages(*, collect_target: int, needs_post_filter: bool, pool_size: bool, has_text_query: bool = False) -> int:
    from app.services.olx.constants import OLX_MAX_SCAN_PAGES, OLX_POOL_MAX_SCAN_PAGES, OLX_RESULTS_PER_PAGE

    cap = OLX_POOL_MAX_SCAN_PAGES if pool_size else OLX_MAX_SCAN_PAGES
    raw_est = collect_target
    if has_text_query:
        # text_query: максимум 3 сторінки — для Zeekr/NIO/тощо вся Україна має <100 оголошень
        return min(3, cap)
    elif needs_post_filter:
        raw_est = max(collect_target * 2, collect_target + OLX_RESULTS_PER_PAGE)
    pages = (raw_est + OLX_RESULTS_PER_PAGE - 1) // OLX_RESULTS_PER_PAGE + 1
    return min(max(int(pages), 1), cap)


def _olx_pool_scan_limits(
    filters: SearchFilters,
    *,
    need: int,
    pool_mode: bool,
) -> tuple[int, int | None]:
    """Обмежує глибину скану OLX для широких фільтрів (ціна без марки тощо)."""
    if not pool_mode:
        return need, None
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if brand or model:
        return min(need, 220), None
    # Без марки OLX не фільтрує ціну в URL — пост-фільтр по всіх авто; 3–4 сторінки достатньо.
    return min(need, 100), 3


async def _fetch_olx_search_html(
    client: OlxClient,
    params: OlxSearchParams,
    filters: SearchFilters,
    *,
    page: int,
) -> tuple[str, OlxSearchParams, str]:
    url = build_search_url(params, page=page)
    try:
        html = await client.fetch_html(url)
        return html, params, url
    except OlxError as exc:
        if (
            exc.status_code == 404
            and not params.text_query
            and (filters.brand or filters.model)
        ):
            bad_url = url
            params = _switch_params_to_text_query(params, filters)
            url = build_search_url(params, page=page)
            try:
                html = await client.fetch_html(url)
                return html, params, url
            except OlxError as retry_exc:
                await notify_admin_parsing_error(
                    source="OLX",
                    error=f"OLX 404 і після fallback: {retry_exc}",
                    url=url,
                    details=f"Перший URL: {bad_url}",
                )
                raise
        if exc.status_code == 404:
            # Не спамимо в Telegram на «голий» 404 без fallback (already tried or N/A)
            pass
        raise


async def _collect_from_params(
    client: OlxClient,
    params: OlxSearchParams,
    filters: SearchFilters,
    *,
    start_page: int,
    target_count: int,
    enrich_sem: asyncio.Semaphore,
    seen: set[str],
    enrich_details: bool = True,
) -> list[OlxListing]:
    """Збирає оголошення з одного набору params (path або /q-/)."""
    collected: list[OlxListing] = []
    pages_scanned = 0
    active = params

    async def enrich_listing(listing: OlxListing) -> OlxListing:
        if not listing.url:
            return listing
        async with enrich_sem:
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            details = await client.fetch_listing_details(listing.url)
        apply_details_to_listing(listing, details)
        return listing

    while pages_scanned < active.max_pages and len(collected) < target_count:
        current_page = start_page + pages_scanned
        try:
            html, active, url = await _fetch_olx_search_html(
                client, active, filters, page=current_page
            )
        except OlxError as exc:
            if exc.status_code == 404 and pages_scanned > 0:
                # 404 на не-першій сторінці = вийшли за межі видачі
                break
            if pages_scanned == 0:
                # Перша сторінка — критична помилка, піднімаємо вгору
                raise
            # Інші помилки на наступних сторінках — пропускаємо, не зупиняємо цикл
            pages_scanned += 1
            continue

        try:
            page_listings = await asyncio.to_thread(parse_listing_page, html)
        except Exception as exc:
            message = f"Виняток при парсингу сторінки видачі OLX: {exc}"
            await notify_admin_parsing_error(
                source="OLX",
                error=message,
                url=url,
                details=type(exc).__name__,
            )
            raise OlxError("Помилка парсингу OLX") from exc

        if not page_listings and pages_scanned == 0 and html_looks_like_results_page(html):
            await asyncio.sleep(1.5)
            try:
                html, active, url = await _fetch_olx_search_html(
                    client, active, filters, page=current_page
                )
                page_listings = await asyncio.to_thread(parse_listing_page, html)
            except OlxError:
                page_listings = []
            except Exception:
                page_listings = []

        # HTML SSR інколи «порожній» (бот/CDN), хоча видача жива — беремо JSON API.
        # API-доповнення викликаємо лише як fallback, щоб не подвоювати запити.
        if not page_listings:
            api_listings = await client.fetch_offers_api(active, page=current_page)
            if api_listings:
                page_listings = api_listings
                url = f"{url} [api-fallback]"

        if not page_listings and pages_scanned == 0 and html_looks_like_results_page(html):
            await notify_admin_parsing_error(
                source="OLX",
                error="Сторінка видачі OLX завантажена, але оголошення не розпарсились",
                url=url,
                details="HTML і API fallback не дали оголошень — перевірте селектори/API",
            )
        if not page_listings:
            break

        candidates: list[OlxListing] = [
            listing for listing in page_listings if passes_olx_filters(listing, active)
        ]
        to_enrich = [
            listing for listing in candidates if listing_needs_enrichment(listing, active)
        ]
        if to_enrich and enrich_details:
            await asyncio.gather(*(enrich_listing(listing) for listing in to_enrich))

        for listing in candidates:
            if not passes_olx_filters(listing, active):
                continue
            key = _listing_dedupe_key(listing)
            if key in seen:
                continue
            seen.add(key)
            collected.append(listing)
            if len(collected) >= target_count:
                break

        pages_scanned += 1
        if not has_next_page(
            html,
            current_page,
            page_listings_count=len(page_listings),
            api_page_limit=OFFERS_API_LIMIT,
        ):
            break
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    return collected


def _cache_key(
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
    enrich_details: bool = True,
) -> str:
    payload = {
        "source": "olx",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
        "enrich": enrich_details,
        "olx_q": "paginate-v2",
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_olx_uncached(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    enrich_details: bool = True,
) -> PaginatedListings:
    """Виконує OLX-пошук: спершу займає слот семафора, потім сканує сторінки.

    Важливо: acquire_olx_slot() НЕ входить у wait_for зовнішнього таймауту,
    тому час очікування в черзі не «з'їдає» бюджет на реальне сканування.
    """
    async with acquire_olx_slot():
        return await _search_olx_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            enrich_details=enrich_details,
        )


async def _search_olx_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    enrich_details: bool = True,
) -> PaginatedListings:
    page = max(page, 1)
    per_page = max(per_page, 1)

    params = filters_to_olx_params(filters, max_pages=2)
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if (
        brand
        and not params.text_query
        and (brand_uses_olx_text_search(brand) or brand_model_forces_text_search(brand, model))
    ):
        params = _switch_params_to_text_query(params, filters)

    needs_pf = params.needs_post_filter()
    has_tq = bool(params.text_query)
    pool_mode = per_page >= 80
    collect_target = _olx_collect_target(
        page=page if not pool_mode else 1,
        per_page=per_page,
        needs_post_filter=needs_pf,
        has_text_query=has_tq,
    )
    scan_need, page_cap = _olx_pool_scan_limits(filters, need=collect_target, pool_mode=pool_mode)
    collect_target = scan_need
    if pool_mode:
        collect_target = min(collect_target, per_page * 2)

    params.max_pages = _olx_max_scan_pages(
        collect_target=collect_target,
        needs_post_filter=needs_pf,
        pool_size=pool_mode,
        has_text_query=has_tq,
    )
    if page_cap is not None:
        params.max_pages = min(params.max_pages, page_cap)

    enrich_sem = asyncio.Semaphore(3)
    seen: set[str] = set()
    collected: list[OlxListing] = []

    text_query = _olx_text_query(filters, params)
    if text_query:
        params.text_query = text_query

    async with OlxClient() as client:
        collected = await _collect_from_params(
            client,
            params,
            filters,
            start_page=1,
            target_count=collect_target,
            enrich_sem=enrich_sem,
            seen=seen,
            enrich_details=enrich_details,
        )

    items = [
        olx_listing_to_listing_out(
            listing,
            brand_hint=filters.brand or "",
            model_hint=filters.model or "",
        )
        for listing in collected
    ]
    from app.services.search.category import listing_matches_category

    if filters.category and filters.category != "all":
        items = [item for item in items if listing_matches_category(item, filters.category)]
    items = sort_listings(items, sort_by)

    slice_start = 0 if pool_mode else (page - 1) * per_page
    slice_end = slice_start + per_page
    page_items = items[slice_start:slice_end]
    total = len(items)
    pages = max((total + per_page - 1) // per_page, 1 if page_items else 0)

    return PaginatedListings(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


async def search_olx(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
    use_cache: bool = True,
    cache_ttl_seconds: int = 120,
    enrich_details: bool = True,
) -> PaginatedListings:
    if not use_cache:
        return await _search_olx_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            enrich_details=enrich_details,
        )

    key = _cache_key(
        filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        enrich_details=enrich_details,
    )
    return await get_or_fetch(
        key,
        lambda: _search_olx_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            enrich_details=enrich_details,
        ),
        ttl_seconds=cache_ttl_seconds,
    )
