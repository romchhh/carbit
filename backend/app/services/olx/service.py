from __future__ import annotations

import asyncio
import json
import random
import re
from dataclasses import replace

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.auto_ria.cache import get_or_fetch
from app.services.auto_ria.mapper import sort_listings
from app.services.olx.brand_slugs import (
    brand_model_forces_text_search,
    brand_uses_olx_text_search,
    build_olx_text_query_variants,
    resolve_olx_brand_slug,
    resolve_olx_text_brand_query,
    slugify,
)
from app.services.olx.client import OlxClient
from app.services.olx.constants import MAX_DELAY, MIN_DELAY
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
    brand_path = resolve_olx_brand_slug(brand) if brand else ""
    brand_q = resolve_olx_text_brand_query(brand) if brand else ""
    if brand_path == "mercedes-benz" and model:
        params.text_query = f"{brand_q} {slugify(model)}"
    elif brand_q and model and re.fullmatch(r"\d+[a-z]?", model, re.IGNORECASE):
        params.text_query = f"{brand_q} {model}"
    elif brand_q:
        params.text_query = brand_q
    elif model:
        params.text_query = model
    else:
        params.text_query = brand
    if brand:
        params.brand_label = brand
    if model:
        params.model_label = model
    params.brand = None
    params.model = None
    return params


def _listing_dedupe_key(listing: OlxListing) -> str:
    if listing.listing_id:
        return f"id:{listing.listing_id}"
    if listing.url:
        return f"url:{listing.url.split('?', 1)[0].rstrip('/')}"
    return f"title:{(listing.title or '').strip().lower()}"


def _normalize_text_query_key(text_query: str | None) -> str:
    return (text_query or "").strip().casefold().replace(" ", "-")


def _build_search_param_variants(
    primary: OlxSearchParams,
    filters: SearchFilters,
) -> list[OlxSearchParams]:
    """Основний запит + альтернативні /q-/ написання марки (mersedes/mercedes/…)."""
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    variants = [primary]
    if not brand:
        return variants

    primary_text_key = _normalize_text_query_key(primary.text_query)
    # Primary на taxonomy-path → text_query порожній; усе одно додаємо folk /q-/
    for query in build_olx_text_query_variants(brand, model):
        key = _normalize_text_query_key(query)
        if not key or key == primary_text_key:
            continue
        if any(_normalize_text_query_key(v.text_query) == key for v in variants):
            continue
        # Альтернативи: 1 сторінка, без brand-path (місто — пост-фільтр)
        alt = replace(
            primary,
            text_query=query,
            brand=None,
            model=None,
            max_pages=1,
        )
        variants.append(alt)
        # Primary + до 3 folk text = max 4 запити
        if len(variants) >= 4:
            break
    return variants


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
        except OlxError:
            # Альтернативний запит може дати 404 — пропускаємо
            break

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
            await notify_admin_parsing_error(
                source="OLX",
                error="Сторінка видачі OLX завантажена, але оголошення не розпарсились",
                url=url,
                details="Ймовірно змінився HTML OLX — перевірте селектори парсера",
            )
        if not page_listings:
            break

        candidates: list[OlxListing] = [
            listing for listing in page_listings if passes_olx_filters(listing, active)
        ]
        to_enrich = [
            listing for listing in candidates if listing_needs_enrichment(listing, active)
        ]
        if to_enrich:
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
        if not has_next_page(html, current_page):
            break
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    return collected


def _cache_key(filters: SearchFilters, *, page: int, per_page: int, sort_by: str) -> str:
    payload = {
        "source": "olx",
        "filters": filters.model_dump(mode="json"),
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
        # bump при зміні multi-query логіки
        "olx_q": "multi-v1",
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


async def _search_olx_uncached(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    async with acquire_olx_slot():
        return await _search_olx_body(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )


async def _search_olx_body(
    filters: SearchFilters,
    *,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "newest",
) -> PaginatedListings:
    # Менше overscan: live path передає вже обмежений per_page (SOURCE_POOL_CAP)
    max_pages = min(max(page, 1) + 1, 3)
    params = filters_to_olx_params(filters, max_pages=max_pages)
    # Подвійний захист: ніколи не бити taxonomy-path для марок/моделей без path на OLX
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    if (
        brand
        and not params.text_query
        and (brand_uses_olx_text_search(brand) or brand_model_forces_text_search(brand, model))
    ):
        params = _switch_params_to_text_query(params, filters)
    if params.needs_post_filter():
        params.max_pages = min(max(params.max_pages, 2), 4)

    start_page = max(page - 1, 0) * 2 + 1
    # Було ×2/×3 — часто впиралось у 15s timeout на великих пулах
    target_count = per_page + max(per_page // 2, 8) if params.needs_post_filter() else per_page
    enrich_sem = asyncio.Semaphore(3)
    seen: set[str] = set()
    collected: list[OlxListing] = []

    param_variants = _build_search_param_variants(params, filters)

    async with OlxClient() as client:
        # Основний запит (path або primary text) — повний обхід сторінок
        primary = param_variants[0]
        collected.extend(
            await _collect_from_params(
                client,
                primary,
                filters,
                start_page=start_page,
                target_count=target_count,
                enrich_sem=enrich_sem,
                seen=seen,
            )
        )

        # Додаткові написання — по 1 сторінці кожне (mersedes / mercedes / мерседес…)
        for alt in param_variants[1:]:
            if len(collected) >= target_count:
                break
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            more = await _collect_from_params(
                client,
                alt,
                filters,
                start_page=1,
                target_count=target_count - len(collected),
                enrich_sem=enrich_sem,
                seen=seen,
            )
            collected.extend(more)

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

    start = 0
    end = per_page
    page_items = items[start:end]
    total = max(len(items), len(page_items))
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
) -> PaginatedListings:
    if not use_cache:
        return await _search_olx_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        )

    key = _cache_key(filters, page=page, per_page=per_page, sort_by=sort_by)
    return await get_or_fetch(
        key,
        lambda: _search_olx_uncached(
            filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
        ),
        ttl_seconds=cache_ttl_seconds,
    )
