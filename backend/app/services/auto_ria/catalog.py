from __future__ import annotations

import asyncio
from typing import Any

from app.core.text import norm_text, bounded_substring
from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.constants import DEFAULT_CATEGORY_ID

_lock = asyncio.Lock()
_marks_cache: list[dict[str, Any]] | None = None
_models_cache: dict[int, list[dict[str, Any]]] = {}


def _normalize_model_key(value: str) -> str:
    """Порівняння моделей: «GLE Coupe» ≈ «GLE-Class Coupe», «купе» ≈ coupe."""
    text = norm_text(value)
    for src, dst in (
        ("(купе)", " coupe "),
        ("(coupe)", " coupe "),
        (" купе", " coupe "),
        ("coupe", " coupe "),
        ("-class", " "),
        (" class", " "),
    ):
        text = text.replace(src, dst)
    return " ".join(text.split())


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
    target = norm_text(brand)
    marks = await _load_marks(client)
    for item in marks:
        if norm_text(str(item.get("name", ""))) == target:
            return int(item["value"])
    for item in marks:
        name = norm_text(str(item.get("name", "")))
        if target in name or name in target:
            return int(item["value"])
    return None


def _model_catalog_match(
    target: str,
    target_key: str,
    name: str,
    name_n: str,
    name_key: str,
) -> bool:
    if target == name_n or target_key == name_key:
        return True
    if target_key and name_key.startswith(target_key):
        return True
    if target_key and bounded_substring(name_key, target_key):
        return True
    if target and bounded_substring(name_n, target):
        return True
    return False


async def resolve_model_id(client: AutoRiaClient, mark_id: int, model: str) -> int | None:
    if not model:
        return None
    target = norm_text(model)
    target_key = _normalize_model_key(model)
    models = await _load_models(client, mark_id)

    for item in models:
        name = str(item.get("name", ""))
        if norm_text(name) == target:
            return int(item["value"])

    for item in models:
        name = str(item.get("name", ""))
        if _normalize_model_key(name) == target_key:
            return int(item["value"])

    # Довші/точніші збіги першими (щоб «C-Class Coupe» не ловився як «C-Class»)
    partial: list[tuple[int, dict[str, Any]]] = []
    for item in models:
        name = str(item.get("name", ""))
        name_n = norm_text(name)
        name_key = _normalize_model_key(name)
        if _model_catalog_match(target, target_key, name, name_n, name_key):
            partial.append((len(name_key), item))
    if partial:
        partial.sort(key=lambda pair: pair[0], reverse=True)
        best_len, best = partial[0]
        # Не підміняти купе седаном/SUV без «coupe» у назві, якщо в запиті є coupe
        if "coupe" in target_key and "coupe" not in _normalize_model_key(str(best.get("name", ""))):
            for length, item in partial:
                if "coupe" in _normalize_model_key(str(item.get("name", ""))):
                    return int(item["value"])
            return None
        return int(best["value"])
    return None
