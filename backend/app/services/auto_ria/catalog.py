from __future__ import annotations

import asyncio
from typing import Any

from app.core.text import bounded_substring, letter_class_canonical, norm_text, unify_class_spelling
from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.constants import DEFAULT_CATEGORY_ID

_lock = asyncio.Lock()
_marks_cache: list[dict[str, Any]] | None = None
_models_cache: dict[int, list[dict[str, Any]]] = {}


def _normalize_model_key(value: str) -> str:
    """Порівняння моделей: «GLE Coupe» ≈ «GLE-Class Coupe», «S-Class» ≈ «S-Класс»."""
    canon = letter_class_canonical(value)
    text = unify_class_spelling(value)
    if canon:
        text = unify_class_spelling(value)
        if "coupe" in text or "купе" in text:
            return f"{canon[0]} coupe"
        return canon
    text = unify_class_spelling(value)
    text = text.replace("-class", " ").replace(" class", " ")
    for src, dst in (
        ("(купе)", " coupe "),
        ("(coupe)", " coupe "),
        (" купе", " coupe "),
        ("coupe", " coupe "),
    ):
        text = text.replace(src, dst)
    return " ".join(text.split())


def _name_has_coupe(name: str) -> bool:
    low = norm_text(name)
    return "coupe" in low or "купе" in low


def _resolve_letter_class_model(
    models: list[dict[str, Any]],
    model: str,
) -> int | None:
    """X-Class / X-Класс — точний збіг без підміни Sprinter/SL через startswith('s')."""
    target_canon = letter_class_canonical(model)
    if not target_canon:
        return None
    wants_coupe = _name_has_coupe(model)

    exact: list[dict[str, Any]] = []
    loose: list[dict[str, Any]] = []
    for item in models:
        name = str(item.get("name", ""))
        item_canon = letter_class_canonical(name)
        if item_canon != target_canon:
            continue
        if wants_coupe:
            if _name_has_coupe(name):
                exact.append(item)
        elif not _name_has_coupe(name):
            exact.append(item)
        else:
            loose.append(item)

    pick_from = exact or loose
    if not pick_from:
        return None
    pick_from.sort(key=lambda row: len(norm_text(str(row.get("name", "")))))
    return int(pick_from[0]["value"])


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
    # «S-Class» → target_key «s-class»; не матчити Sprinter/SL через startswith('s').
    if len(target_key) <= 2:
        return False
    if target_key and name_key.startswith(target_key):
        return True
    if target_key and bounded_substring(name_key, target_key):
        return True
    if target and bounded_substring(name_n, target):
        return True
    return False


async def resolve_named_model_id(client: AutoRiaClient, mark_id: int, model: str) -> int | None:
    """Exact / normalized name first — so «C-Class All-Terrain» ≠ shortest «C-Class»."""
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
        if target_key and _normalize_model_key(name) == target_key:
            return int(item["value"])
    return await resolve_model_id(client, mark_id, model)


async def resolve_new_search_model_ids(
    client: AutoRiaClient,
    brand: str,
    model: str,
) -> list[int]:
    """Primary model plus new-generation aliases (A4→A5, C-Class→CLE)."""
    if not brand or not model:
        return []
    mark_id = await resolve_mark_id(client, brand)
    if mark_id is None:
        return []
    from app.services.search.new_generation import new_generation_models

    ids: list[int] = []
    seen: set[int] = set()
    for name in new_generation_models(brand, model):
        mid = await resolve_named_model_id(client, mark_id, name)
        if mid is None or mid in seen:
            continue
        seen.add(mid)
        ids.append(mid)
    return ids


async def resolve_model_id(client: AutoRiaClient, mark_id: int, model: str) -> int | None:
    if not model:
        return None
    target = norm_text(model)
    target_key = _normalize_model_key(model)
    models = await _load_models(client, mark_id)

    letter_class_id = _resolve_letter_class_model(models, model)
    if letter_class_id is not None:
        return letter_class_id

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


async def model_filter_needs_post_filter(client: AutoRiaClient, filters) -> bool:
    """True, якщо AUTO.RIA не має точного model_id — потрібен пост-фільтр по title/model."""
    model = (getattr(filters, "model", None) or "").strip()
    brand = (getattr(filters, "brand", None) or "").strip()
    if not model or not brand:
        return False
    mark_id = await resolve_mark_id(client, brand)
    if mark_id is None:
        return False
    return await resolve_model_id(client, mark_id, model) is None
