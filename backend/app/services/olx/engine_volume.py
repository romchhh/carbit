"""Обʼєм двигуна з OLX specs / params[]."""

from __future__ import annotations

import re
from typing import Any

from app.services.listings.engine_volume import normalize_engine_litres

_APOSTROPHE_RE = re.compile(r"[''`´ʼ]")

# Внутрішні ключі OLX params[] (UA).
_ENGINE_PARAM_KEYS = frozenset(
    {
        "engine_capacity",
        "motor_engine_size",
        "engine_size",
        "enginevolume",
        "engine_volume",
        "motor_engine",
        "motor_engine_size_litre",
    }
)


def normalize_olx_spec_key(key: str) -> str:
    text = (key or "").strip().lower()
    return _APOSTROPHE_RE.sub("'", text)


def _key_is_engine_volume(spec_key: str, param_key: str = "") -> bool:
    key = normalize_olx_spec_key(spec_key)
    pk = normalize_olx_spec_key(param_key)
    if pk in _ENGINE_PARAM_KEYS:
        return True
    if "engine" in pk and any(token in pk for token in ("capacity", "size", "volume")):
        return True
    if "об" in key and "єм" in key:
        return True
    if "объем" in key or "обьем" in key:
        return True
    if "engine" in key and any(token in key for token in ("volume", "capacity", "size")):
        return True
    if key in {"engine", "motor", "двигун", "мотор"}:
        return True
    return False


def parse_olx_engine_spec_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return normalize_engine_litres(float(value))
    if isinstance(value, list):
        for item in value:
            parsed = parse_olx_engine_spec_value(item)
            if parsed is not None:
                return parsed
        return None
    if not isinstance(value, str):
        value = str(value)
    text = value.strip()
    if not text:
        return None

    match = re.search(r"([\d]+[.,]?\d*)\s*(?:л|l|litre|liter|літр)\b", text, re.I)
    if match:
        return normalize_engine_litres(float(match.group(1).replace(",", ".")))

    match = re.search(r"([\d]{3,4})\s*(?:см3|см³|cc|куб\.?|cm3)\b", text, re.I)
    if match:
        return normalize_engine_litres(float(match.group(1)))

    match = re.search(r"([\d]+[.,]?\d*)", text.replace(" ", ""))
    if match:
        return normalize_engine_litres(float(match.group(1).replace(",", ".")))
    return None


def extract_engine_volume_from_specs(specs: dict[str, Any] | None) -> float | None:
    if not isinstance(specs, dict):
        return None
    for spec_key, spec_value in specs.items():
        if str(spec_key).startswith("__"):
            continue
        if _key_is_engine_volume(str(spec_key)):
            parsed = parse_olx_engine_spec_value(spec_value)
            if parsed is not None:
                return parsed
    return None


def extract_engine_volume_from_raw_params(raw_params: dict[str, Any] | None) -> float | None:
    if not isinstance(raw_params, dict):
        return None
    params = raw_params.get("params")
    if not isinstance(params, list):
        return None

    from app.services.olx.parser import _param_value_text

    for item in params:
        if not isinstance(item, dict):
            continue
        param_key = str(item.get("key") or "").strip()
        param_name = str(item.get("name") or "").strip()
        if not _key_is_engine_volume(param_name, param_key):
            continue
        value = _param_value_text(item.get("value") if "value" in item else item.get("normalizedValue"))
        parsed = parse_olx_engine_spec_value(value)
        if parsed is not None:
            return parsed
    return None


def extract_olx_listing_engine_volume(listing: Any) -> float | None:
    """OlxListing або dict з specs/raw_params."""
    specs = getattr(listing, "specs", None)
    if specs is None and isinstance(listing, dict):
        specs = listing.get("specs")

    parsed = extract_engine_volume_from_specs(specs if isinstance(specs, dict) else None)
    if parsed is not None:
        return parsed

    raw_params = getattr(listing, "raw_params", None)
    if raw_params is None and isinstance(listing, dict):
        raw_params = listing.get("raw_params")
    return extract_engine_volume_from_raw_params(raw_params if isinstance(raw_params, dict) else None)
