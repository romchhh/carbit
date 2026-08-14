from __future__ import annotations

import asyncio
from typing import Any

from app.core.text import norm_text
from app.services.udrive.client import UdriveClient

_lock = asyncio.Lock()
_makes_cache: list[dict[str, Any]] | None = None
_models_cache: dict[int, list[dict[str, Any]]] = {}
_makes_by_id: dict[int, dict[str, Any]] | None = None


def _norm_slug(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "-")


async def _load_makes(client: UdriveClient) -> list[dict[str, Any]]:
    global _makes_cache, _makes_by_id
    if _makes_cache is not None:
        return _makes_cache
    async with _lock:
        if _makes_cache is None:
            _makes_cache = await client.list_makes()
            _makes_by_id = {
                int(item["id"]): item
                for item in _makes_cache
                if item.get("id") is not None
            }
    return _makes_cache


async def get_makes_by_id(client: UdriveClient) -> dict[int, dict[str, Any]]:
    await _load_makes(client)
    return _makes_by_id or {}


async def _load_models(client: UdriveClient, make_id: int) -> list[dict[str, Any]]:
    if make_id in _models_cache:
        return _models_cache[make_id]
    async with _lock:
        if make_id not in _models_cache:
            _models_cache[make_id] = await client.list_models(make_id)
    return _models_cache[make_id]


async def resolve_make(client: UdriveClient, brand: str) -> dict[str, Any] | None:
    if not brand:
        return None
    from app.services.search.brand_model_keywords import collect_brand_keyword_variants

    target = norm_text(brand)
    variants = {norm_text(v) for v in collect_brand_keyword_variants(brand) if v.strip()}
    variants.add(target)
    slug_target = _norm_slug(brand)

    makes = await _load_makes(client)
    for item in makes:
        name = norm_text(str(item.get("name") or ""))
        slug = _norm_slug(str(item.get("slug") or ""))
        if name == target or name in variants or slug == slug_target:
            return item

    for item in makes:
        name = norm_text(str(item.get("name") or ""))
        slug = _norm_slug(str(item.get("slug") or ""))
        for variant in variants:
            if not variant:
                continue
            if variant in name or name in variant or variant.replace(" ", "-") == slug:
                return item
    return None


async def resolve_model_ids(
    client: UdriveClient,
    make_id: int,
    model: str,
    *,
    brand: str = "",
) -> list[int]:
    if not model:
        return []

    from app.services.search.brand_model_keywords import collect_model_keyword_variants

    q = model.strip().lower()
    q_norm = norm_text(model)
    variants = {norm_text(v) for v in collect_model_keyword_variants(brand, model) if v.strip()}
    variants.add(q_norm)

    models = await _load_models(client, make_id)

    exact_slug = [m for m in models if (m.get("slug") or "").lower() == q]
    if exact_slug:
        series = [
            m
            for m in models
            if (m.get("slug") or "").lower() == q
            or (m.get("slug") or "").lower().startswith(q + "-")
        ]
        return [int(m["id"]) for m in (series or exact_slug) if m.get("id") is not None]

    by_prefix = [
        m
        for m in models
        if (m.get("slug") or "").lower() == q
        or (m.get("slug") or "").lower().startswith(q + "-")
    ]
    if by_prefix:
        return [int(m["id"]) for m in by_prefix if m.get("id") is not None]

    by_name: list[dict[str, Any]] = []
    for m in models:
        name_n = norm_text(str(m.get("name") or ""))
        if name_n in variants or any(name_n.startswith(v + " ") for v in variants if v):
            by_name.append(m)
    if by_name:
        return [int(m["id"]) for m in by_name if m.get("id") is not None]

    soft = [
        m
        for m in models
        if q in (m.get("slug") or "").lower()
        or any(v and v in norm_text(str(m.get("name") or "")).split() for v in variants)
    ]
    return [int(m["id"]) for m in soft if m.get("id") is not None]
