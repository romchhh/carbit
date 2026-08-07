"""Multi-value brand/model/region helpers for search filters."""

from __future__ import annotations

from app.core.text import norm_text
from app.schemas.schemas import SearchFilters

MAX_BRAND_FANOUT = 4
ALL_UKRAINE = frozenset({"вся україна", "ukraine", "всі регіони", ""})


def effective_brands(filters: SearchFilters) -> list[str]:
    brands = [b.strip() for b in (filters.brands or []) if b and str(b).strip()]
    if brands:
        return brands
    brand = (filters.brand or "").strip()
    return [brand] if brand else []


def effective_models(filters: SearchFilters) -> list[str]:
    models = [m.strip() for m in (filters.models or []) if m and str(m).strip()]
    if models:
        return models
    model = (filters.model or "").strip()
    return [model] if model else []


def effective_regions(filters: SearchFilters) -> list[str]:
    regions = [r.strip() for r in (filters.regions or []) if r and str(r).strip()]
    if regions:
        return [r for r in regions if norm_text(r) not in ALL_UKRAINE]
    region = (filters.region or "").strip()
    if region and norm_text(region) not in ALL_UKRAINE:
        return [region]
    return []


def sync_multi_search_filters(filters: SearchFilters) -> SearchFilters:
    """Normalize singular + plural brand/model/region fields."""
    brands = effective_brands(filters)
    models = effective_models(filters)
    regions = effective_regions(filters)

    update: dict = {
        "brands": brands or None,
        "models": models or None,
        "regions": regions or None,
        "brand": brands[0] if brands else None,
        "model": models[0] if models else None,
    }
    if len(regions) == 1:
        update["region"] = regions[0]
    elif regions:
        update["region"] = None
    else:
        update["region"] = filters.region if filters.region else None

    return filters.model_copy(update=update)


def expand_filters_for_api_fetch(filters: SearchFilters) -> list[SearchFilters]:
    """
    Fan-out by brand for live API calls (AUTO.RIA / OLX).
    Multiple models/regions are handled via post-filtering.
    """
    synced = sync_multi_search_filters(filters)
    brands = effective_brands(synced)
    models = effective_models(synced)
    regions = effective_regions(synced)

    if len(brands) <= 1:
        variants = [synced.model_copy(deep=True)]
    else:
        variants = []
        for brand in brands[:MAX_BRAND_FANOUT]:
            v = synced.model_copy(deep=True)
            v.brand = brand
            v.brands = [brand]
            variants.append(v)

    out: list[SearchFilters] = []
    for variant in variants:
        v = variant.model_copy(deep=True)
        if len(models) > 1:
            v.model = None
            v.models = models
        elif len(models) == 1:
            v.model = models[0]
            v.models = models
        if len(regions) > 1:
            v.region = None
            v.regions = regions
        out.append(v)
    return out


def needs_api_fanout(filters: SearchFilters) -> bool:
    return len(effective_brands(filters)) > 1
