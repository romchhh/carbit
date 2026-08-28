"""Multi-value brand/model/region helpers for search filters."""

from __future__ import annotations

from app.core.text import norm_text
from app.schemas.schemas import SearchFilters
from app.services.search.region_voice import normalize_region_label

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


def canonicalize_region(value: str | None) -> str | None:
    """«Хмельницька» / «волинській області» → «Хмельницька область»."""
    text = (value or "").strip()
    if not text or norm_text(text) in ALL_UKRAINE:
        return None
    return normalize_region_label(text) or text


def effective_regions(filters: SearchFilters) -> list[str]:
    regions = [r.strip() for r in (filters.regions or []) if r and str(r).strip()]
    if not regions:
        region = (filters.region or "").strip()
        regions = [region] if region else []

    out: list[str] = []
    seen: set[str] = set()
    for raw in regions:
        canonical = canonicalize_region(raw)
        if not canonical:
            continue
        key = norm_text(canonical)
        if key in ALL_UKRAINE or key in seen:
            continue
        seen.add(key)
        out.append(canonical)
    return out


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
