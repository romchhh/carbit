from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import SearchFilters
from app.services.reono.constants import REONO_CATALOG_PATH, REONO_REGION_SEGMENTS, REGION_SLUGS
from app.services.search.filter_multi import effective_brands
from app.services.search.subbrand_split import split_huawei_subbrand

_CITY_PREFIX_RE = re.compile(r"^м\.\s*", re.IGNORECASE)


def _slugify_latin(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text


def resolve_reono_region_segments(region: str | None) -> list[str]:
    if not region:
        return []
    raw = region.strip()
    if not raw:
        return []

    keys: list[str] = [norm_text(raw)]
    stripped = _CITY_PREFIX_RE.sub("", raw).strip()
    if stripped and norm_text(stripped) not in keys:
        keys.append(norm_text(stripped))

    for key in keys:
        if key in ("вся україна", "всі регіони"):
            return []
        segments = REONO_REGION_SEGMENTS.get(key)
        if segments:
            return list(segments)
        slug = REGION_SLUGS.get(key)
        if slug:
            return [slug]

    return []


def filters_to_catalog_path(filters: SearchFilters, *, page: int) -> str:
    segments = [REONO_CATALOG_PATH]
    segments.extend(resolve_reono_region_segments(filters.region))

    brands = effective_brands(filters)
    if brands:
        brand, _model = split_huawei_subbrand(brands[0], (filters.model or "").strip())
        brand_slug = _slugify_latin(brand)
        if brand_slug:
            segments.append(brand_slug)
        model = (filters.model or "").strip()
        if model:
            model_slug = _slugify_latin(model)
            if model_slug:
                segments.append(model_slug)

    path = "/".join(segments)
    if page > 1:
        path = f"{path}/page={page}"
    return path


def catalog_path_fallbacks(filters: SearchFilters, *, page: int) -> list[str]:
    """Шляхи від точнішого до ширшого — для 404 на REONO."""
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        if path not in seen:
            seen.add(path)
            paths.append(path)

    add(filters_to_catalog_path(filters, page=page))

    if filters.region:
        add(
            filters_to_catalog_path(
                filters.model_copy(update={"region": None}),
                page=page,
            )
        )

    if filters.model:
        add(
            filters_to_catalog_path(
                filters.model_copy(update={"model": None}),
                page=page,
            )
        )

    if filters.region or filters.model:
        add(
            filters_to_catalog_path(
                filters.model_copy(update={"region": None, "model": None}),
                page=page,
            )
        )

    return paths
