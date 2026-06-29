from __future__ import annotations

import asyncio
from typing import Any

from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.constants import DEFAULT_CATEGORY_ID

_lock = asyncio.Lock()
_marks_cache: list[dict[str, Any]] | None = None
_models_cache: dict[int, list[dict[str, Any]]] = {}


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


async def _load_marks(client: AutoRiaClient) -> list[dict[str, Any]]:
    global _marks_cache
    if _marks_cache is not None:
        return _marks_cache
    async with _lock:
        if _marks_cache is None:
            _marks_cache = await client.get_marks(DEFAULT_CATEGORY_ID)
    return _marks_cache


async def _load_models(client: AutoRiaClient, mark_id: int) -> list[dict[str, Any]]:
    if mark_id in _models_cache:
        return _models_cache[mark_id]
    async with _lock:
        if mark_id not in _models_cache:
            _models_cache[mark_id] = await client.get_models(mark_id, DEFAULT_CATEGORY_ID)
    return _models_cache[mark_id]


async def resolve_mark_id(client: AutoRiaClient, brand: str) -> int | None:
    if not brand:
        return None
    target = _norm(brand)
    marks = await _load_marks(client)
    for item in marks:
        if _norm(str(item.get("name", ""))) == target:
            return int(item["value"])
    for item in marks:
        name = _norm(str(item.get("name", "")))
        if target in name or name in target:
            return int(item["value"])
    return None


async def resolve_model_id(client: AutoRiaClient, mark_id: int, model: str) -> int | None:
    if not model:
        return None
    target = _norm(model)
    models = await _load_models(client, mark_id)
    for item in models:
        if _norm(str(item.get("name", ""))) == target:
            return int(item["value"])
    for item in models:
        name = _norm(str(item.get("name", "")))
        if target in name or name in target:
            return int(item["value"])
    return None
