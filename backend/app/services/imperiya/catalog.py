from __future__ import annotations

import asyncio
import re
from typing import Any

from app.core.text import bounded_substring, norm_text
from app.services.imperiya.client import ImperiyaClient

_lock = asyncio.Lock()
_makes_cache: list[dict[str, Any]] | None = None
_models_cache: dict[int, list[dict[str, Any]]] = {}
_regions_cache: list[dict[str, Any]] | None = None

# UA/RU «клас/серия» ↔ latin class/series для зіставлення з FE-назвами.
_CLASS_TOKENS = re.compile(r"класс|клас|klass|class", re.IGNORECASE)
_SERIES_TOKENS = re.compile(r"серии|серії|seriyi|seriya|series", re.IGNORECASE)


def _imperiya_model_key(text: str) -> str:
    t = norm_text(text or "")
    t = _CLASS_TOKENS.sub("class", t)
    t = _SERIES_TOKENS.sub("series", t)
    return re.sub(r"\s+", " ", t).strip()


def _model_variant_keys(brand: str, model: str) -> set[str]:
    from app.services.search.brand_model_keywords import collect_model_keyword_variants

    keys: set[str] = set()
    for raw in (model,):
        if raw.strip():
            keys.add(norm_text(raw))
            keys.add(_imperiya_model_key(raw))
    for variant in collect_model_keyword_variants(brand, model):
        if not variant.strip():
            continue
        keys.add(norm_text(variant))
        keys.add(_imperiya_model_key(variant))
    return {k for k in keys if k}


def _brand_variant_keys(brand: str) -> set[str]:
    from app.services.search.brand_model_keywords import collect_brand_keyword_variants

    keys: set[str] = set()
    for variant in collect_brand_keyword_variants(brand):
        if variant.strip():
            keys.add(norm_text(variant))
    return keys


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
    variants = _brand_variant_keys(brand)
    makes = await _load_makes(client)

    for item in makes:
        name = norm_text(str(item.get("name", "")))
        if name == target or name in variants:
            return int(item["id"])

    for item in makes:
        name = norm_text(str(item.get("name", "")))
        slug = norm_text(str(item.get("slug", "")).replace("-", " "))
        for variant in variants | {target}:
            if not variant:
                continue
            if variant == name or variant == slug:
                return int(item["id"])
            if variant in name or name in variant:
                return int(item["id"])
            if variant.replace(" ", "") in slug.replace(" ", ""):
                return int(item["id"])
    return None


def _score_model_match(item: dict[str, Any], variant_keys: set[str], *, model: str) -> int:
    name = str(item.get("name", "")).strip()
    if not name:
        return 0
    name_n = norm_text(name)
    name_k = _imperiya_model_key(name)
    slug = norm_text(str(item.get("slug", "")).replace("-", " "))

    best = 0
    model_wants_amg = "amg" in norm_text(model)
    item_is_amg = "amg" in name_n

    for key in variant_keys:
        if not key:
            continue
        if name_n == key or name_k == key:
            best = max(best, 100)
        elif slug == key or key in slug or slug in key:
            best = max(best, 90)
        elif bounded_substring(name_k, key) or bounded_substring(key, name_k):
            best = max(best, 70)
        elif bounded_substring(name_n, key) or bounded_substring(key, name_n):
            best = max(best, 60)

    if best >= 70 and item_is_amg and not model_wants_amg:
        best -= 15
    return best


async def resolve_model_id(
    client: ImperiyaClient,
    make_id: int,
    model: str,
    *,
    brand: str = "",
) -> int | None:
    if not model:
        return None

    models = await _load_models(client, make_id)
    variant_keys = _model_variant_keys(brand, model)

    # Точний match за назвою.
    target = norm_text(model)
    for item in models:
        if norm_text(str(item.get("name", ""))) == target:
            return int(item["id"])

    # Alias / FE / UA-RU class-series keys.
    scored: list[tuple[int, int]] = []
    for item in models:
        score = _score_model_match(item, variant_keys, model=model)
        if score > 0:
            scored.append((score, int(item["id"])))
    if scored:
        scored.sort(key=lambda row: (-row[0], row[1]))
        return scored[0][1]

    # Legacy substring fallback.
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
