from __future__ import annotations

import asyncio
from typing import Any

from app.core.text import bounded_substring, norm_text
from app.services.imperiya.client import ImperiyaClient

_lock = asyncio.Lock()
_makes_cache: list[dict[str, Any]] | None = None
_models_cache: dict[int, list[dict[str, Any]]] = {}
_regions_cache: list[dict[str, Any]] | None = None


async def _load_makes(client: ImperiyaClient) -> list[dict[str, Any]]:
    global _makes_cache
    if _makes_cache is not None:
        return _makes_cache
    async with _lock:
        if _makes_cache is None:
            _makes_cache = await client.list_makes()
    return _makes_cache


async def _load_models(client: ImperiyaClient, make_id: int) -> list[dict[str, Any]]:
    if make_id in _models_cache:
        return _models_cache[make_id]
    async with _lock:
        if make_id not in _models_cache:
            _models_cache[make_id] = await client.list_models(make_id)
    return _models_cache[make_id]


async def _load_regions(client: ImperiyaClient) -> list[dict[str, Any]]:
    global _regions_cache
    if _regions_cache is not None:
        return _regions_cache
    async with _lock:
        if _regions_cache is None:
            _regions_cache = await client.list_regions()
    return _regions_cache


async def resolve_make_id(client: ImperiyaClient, brand: str) -> int | None:
    if not brand:
        return None
    target = norm_text(brand)
    makes = await _load_makes(client)
    for item in makes:
        if norm_text(str(item.get("name", ""))) == target:
            return int(item["id"])
    for item in makes:
        name = norm_text(str(item.get("name", "")))
        if target in name or name in target:
            return int(item["id"])
    return None


async def resolve_model_id(client: ImperiyaClient, make_id: int, model: str) -> int | None:
    if not model:
        return None
    target = norm_text(model)
    models = await _load_models(client, make_id)
    for item in models:
        if norm_text(str(item.get("name", ""))) == target:
            return int(item["id"])
    for item in models:
        name = norm_text(str(item.get("name", "")))
        if bounded_substring(name, target) or bounded_substring(target, name):
            return int(item["id"])
    return None


def _carbit_region_key(region: str) -> str:
    text = norm_text(region)
    text = text.removeprefix("м ").strip()
    text = text.replace(" область", "").strip()
    return text


async def resolve_region_ids(client: ImperiyaClient, region: str) -> list[int]:
    if not region or norm_text(region) in ("вся україна", "всі регіони", ""):
        return []
    key = _carbit_region_key(region)
    regions = await _load_regions(client)
    ids: list[int] = []
    for item in regions:
        name = norm_text(str(item.get("name", "")))
        if name == key or key in name or name in key:
            ids.append(int(item["id"]))
    return ids


async def resolve_region_ids_for_filters(client: ImperiyaClient, regions: list[str]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for region in regions:
        for rid in await resolve_region_ids(client, region):
            if rid not in seen:
                seen.add(rid)
                out.append(rid)
    return out
