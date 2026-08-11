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
    """Normalize singular + plural brand/model/region fields (single value only)."""
    brand = (effective_brands(filters)[:1] or [None])[0]
    model = (effective_models(filters)[:1] or [None])[0]
    region = (effective_regions(filters)[:1] or [None])[0]

    return filters.model_copy(
        update={
            "brands": [brand] if brand else None,
            "models": [model] if model else None,
            "regions": [region] if region else None,
            "brand": brand,
            "model": model,
            "region": region,
        }
    )


def expand_filters_for_api_fetch(filters: SearchFilters) -> list[SearchFilters]:
    """One variant per search — multi-brand fan-out disabled."""
    return [sync_multi_search_filters(filters).model_copy(deep=True)]


def needs_api_fanout(filters: SearchFilters) -> bool:
    return False
