from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.schemas.schemas import SearchFilters


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


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
    return data


def filters_group_key(filters: SearchFilters | dict) -> str:
    payload = json.dumps(filters_to_dict(filters), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


@dataclass
class FilterGroup:
    key: str
    filters: SearchFilters
    search_ids: list[str]


def group_searches(searches: list[tuple[str, dict]]) -> list[FilterGroup]:
    """Групує збережені пошуки за однаковими фільтрами."""
    buckets: dict[str, FilterGroup] = {}

    for search_id, raw_filters in searches:
        filters = SearchFilters.model_validate(raw_filters)
        key = filters_group_key(filters)
        if key not in buckets:
            buckets[key] = FilterGroup(key=key, filters=filters, search_ids=[])
        buckets[key].search_ids.append(search_id)

    return list(buckets.values())
