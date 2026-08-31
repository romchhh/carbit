from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from app.core.text import norm_text
from app.schemas.schemas import SearchFilters


def parse_search_filters(raw: SearchFilters | dict | None) -> SearchFilters:
    if raw is None:
        return SearchFilters()
    if isinstance(raw, SearchFilters):
        return raw
    return SearchFilters.model_validate(raw)


def filters_to_dict(filters: SearchFilters | dict) -> dict:
    if isinstance(filters, SearchFilters):
        data = filters.model_dump(exclude_none=True)
    else:
        data = {k: v for k, v in filters.items() if v is not None}
    if sources := data.get("sources"):
        data["sources"] = sorted(sources)
    if fuels := data.get("fuel"):
        data["fuel"] = sorted(fuels)
    if trans := data.get("transmission"):
        data["transmission"] = sorted(trans)
    if drives := data.get("drivetrain"):
        data["drivetrain"] = sorted(drives)
    if colors := data.get("colors"):
        data["colors"] = sorted(colors)
    if brands := data.get("brands"):
        data["brands"] = sorted(brands)
    if models := data.get("models"):
        data["models"] = sorted(models)
    if regions := data.get("regions"):
        data["regions"] = sorted(regions)
    return data


def filters_group_key(filters: SearchFilters | dict) -> str:
    payload = json.dumps(filters_to_dict(filters), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def _normalized_sources(sources: list[str] | None) -> tuple[str, ...]:
    default = ("auto_ria", "olx", "car_market", "lubeavto", "reono", "imperiya", "udrive", "telegram")
    if not sources:
        return default
    out: list[str] = []
    for raw in sources:
        key = raw.strip().lower().replace(".", "_").replace(" ", "_")
        if key in ("auto_ria", "autoria") and "auto_ria" not in out:
            out.append("auto_ria")
        elif key == "olx" and "olx" not in out:
            out.append("olx")
        elif key in ("imperiya", "imperiya_auto", "imperiya-auto", "iautos") and "imperiya" not in out:
            out.append("imperiya")
        elif key in ("udrive", "u_drive", "u-drive") and "udrive" not in out:
            out.append("udrive")
        elif key in ("car_market", "carmarket", "car-market", "car_market_net") and "car_market" not in out:
            out.append("car_market")
        elif key in ("lubeavto", "lube_avto", "lube-avto", "любе_авто", "любеавто") and "lubeavto" not in out:
            out.append("lubeavto")
        elif key in ("reono", "reono_ua", "reono-ua") and "reono" not in out:
            out.append("reono")
        elif key == "telegram" and "telegram" not in out:
            out.append("telegram")
    return tuple(out or default)


def similar_fetch_signature(filters: SearchFilters) -> str | None:
    """
    Ключ для групування «схожих» пошуків (та сама марка/модель/категорія/джерела).
    None — без марки: групуємо лише за точним збігом.
    """
    brand = norm_text(filters.brand or "")
    if not brand:
        return None
    model = norm_text(filters.model or "")
    category = (filters.category or "all").strip().lower()
    sources = _normalized_sources(filters.sources)
    payload = f"{brand}|{model}|{category}|{'|'.join(sources)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _merge_min_values(values: list[int | None]) -> int | None:
    present = [v for v in values if v is not None]
    return min(present) if present else None


def _merge_max_values(values: list[int | None]) -> int | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None


def _merge_float_min_values(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return min(present) if present else None


def _merge_float_max_values(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None


def _merge_list_union(values: list[list[str] | None]) -> list[str] | None:
    sets = [frozenset(v) for v in values if v]
    if not sets:
        return None
    if len(sets) == 1:
        return sorted(sets[0])
    merged = set().union(*sets)
    return sorted(merged)


def _merge_region(values: list[str | None]) -> str | None:
    normalized = [norm_text(v) for v in values if v]
    if not normalized:
        return None
    if any(r in ("вся україна", "ukraine", "") for r in normalized):
        return None
    if len(set(normalized)) == 1:
        return values[normalized.index(normalized[0])]
    return None


def _merge_currency(values: list[str | None]) -> str | None | Literal["MIXED"]:
    normalized = [str(v).upper() for v in values if v]
    if not normalized:
        return None
    if len(set(normalized)) == 1:
        return normalized[0]
    return "MIXED"


def merge_filters_for_fetch(filters_list: list[SearchFilters]) -> SearchFilters:
    """
    Об'єднує фільтри групи в «ширший» запит до API.
    Лінкування до кожного пошуку — окремо, за його власними фільтрами.
    """
    if not filters_list:
        return SearchFilters()
    if len(filters_list) == 1:
        return filters_list[0]

    merged = filters_list[0].model_copy()
    merged.year_from = _merge_min_values([f.year_from for f in filters_list])
    merged.year_to = _merge_max_values([f.year_to for f in filters_list])
    merged.mileage_from = _merge_min_values([f.mileage_from for f in filters_list])
    merged.mileage_to = _merge_max_values([f.mileage_to for f in filters_list])
    merged.engine_volume_from = _merge_float_min_values([f.engine_volume_from for f in filters_list])
    merged.engine_volume_to = _merge_float_max_values([f.engine_volume_to for f in filters_list])
    merged.power_from = _merge_min_values([f.power_from for f in filters_list])
    merged.power_to = _merge_max_values([f.power_to for f in filters_list])
    merged.seats_from = _merge_min_values([f.seats_from for f in filters_list])
    merged.seats_to = _merge_max_values([f.seats_to for f in filters_list])
    merged.doors_from = _merge_min_values([f.doors_from for f in filters_list])
    merged.doors_to = _merge_max_values([f.doors_to for f in filters_list])

    merged.region = _merge_region([f.region for f in filters_list])
    merged.regions = _merge_list_union([f.regions for f in filters_list])
    merged.brands = _merge_list_union([f.brands for f in filters_list])
    merged.models = _merge_list_union([f.models for f in filters_list])
    merged.fuel = _merge_list_union([f.fuel for f in filters_list])
    merged.transmission = _merge_list_union([f.transmission for f in filters_list])
    merged.drivetrain = _merge_list_union([f.drivetrain for f in filters_list])
    merged.colors = _merge_list_union([f.colors for f in filters_list])
    merged.body_types = _merge_list_union([f.body_types for f in filters_list])

    currency = _merge_currency([f.currency for f in filters_list])
    if currency != "MIXED":
        merged.currency = None if currency is None else currency
        merged.price_from = _merge_min_values([f.price_from for f in filters_list])
        merged.price_to = _merge_max_values([f.price_to for f in filters_list])
    else:
        merged.currency = None
        merged.price_from = None
        merged.price_to = None

    source_union: set[str] = set()
    for f in filters_list:
        source_union.update(_normalized_sources(f.sources))
    merged.sources = sorted(source_union)
    return merged


@dataclass
class FilterGroup:
    key: str
    filters: SearchFilters
    search_ids: list[str]
    similar: bool = False


def group_searches(
    searches: list[tuple[str, dict]],
    *,
    similar: bool = False,
) -> list[FilterGroup]:
    """
    Групує збережені пошуки.

    similar=False — лише ідентичні фільтри (default для exact cache keys).
    similar=True — одна марка/модель/категорія, різні роки/ціни → один fetch.
    """
    if not similar:
        buckets: dict[str, FilterGroup] = {}
        for search_id, raw_filters in searches:
            filters = SearchFilters.model_validate(raw_filters)
            key = filters_group_key(filters)
            if key not in buckets:
                buckets[key] = FilterGroup(key=key, filters=filters, search_ids=[])
            buckets[key].search_ids.append(search_id)
        return list(buckets.values())

    exact_buckets: dict[str, FilterGroup] = {}
    similar_buckets: dict[str, list[tuple[str, SearchFilters]]] = {}

    for search_id, raw_filters in searches:
        filters = SearchFilters.model_validate(raw_filters)
        sig = similar_fetch_signature(filters)
        if sig is None:
            key = filters_group_key(filters)
            if key not in exact_buckets:
                exact_buckets[key] = FilterGroup(key=key, filters=filters, search_ids=[])
            exact_buckets[key].search_ids.append(search_id)
            continue
        similar_buckets.setdefault(sig, []).append((search_id, filters))

    groups: list[FilterGroup] = list(exact_buckets.values())
    for sig, members in similar_buckets.items():
        filters_list = [f for _, f in members]
        merged = merge_filters_for_fetch(filters_list)
        groups.append(
            FilterGroup(
                key=f"sim-{sig}",
                filters=merged,
                search_ids=[sid for sid, _ in members],
                similar=True,
            )
        )
    return groups


def search_monitor_display_name(search) -> str:
    """Підпис моніторингу для Telegram — з фільтрів, не лише з поля name."""
    filters = parse_search_filters(getattr(search, "filters", None))
    parts: list[str] = []
    if filters.brand:
        parts.append(filters.brand.strip())
    if filters.model:
        parts.append(filters.model.strip())
    label = " · ".join(parts)
    region = (filters.region or "").strip()
    if region and norm_text(region) not in ("вся україна", ""):
        region_short = region.removeprefix("м.").removeprefix("М.").strip()
        label = f"{label} · {region_short}" if label else region_short
    if label:
        return label
    custom = (getattr(search, "name", None) or "").strip()
    return custom or "Мій моніторинг"


def listing_matches_search_query(listing, search) -> bool:
    """Чи oголошення відповідає фільтрам збереженого моніторингу."""
    from app.services.listings.serialize import listing_to_out
    from app.services.telegram_channels.mapper import listing_out_matches_filters

    item = listing_to_out(listing)
    filters = parse_search_filters(getattr(search, "filters", None))
    return listing_out_matches_filters(item, filters)
