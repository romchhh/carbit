"""Визначення обʼєму двигуна (л) з полів оголошення та тексту."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

_APOSTROPHE_RE = re.compile(r"[''`´ʼ]")

# Повні слова палива — стебла «бенз»/«диз» + \b не матчать «бензин»/«дизель».
_FUEL_WORD = (
    r"бензин(?:овий)?|дизель(?:ний|не)?|дизел|газ(?:овий)?|"
    r"hybrid|petrol|diesel|benzin|dizel|gasoline"
)
_ENGINE_TRANS_HINT = (
    rf"at|mt|cvt|dsg|tiptronic|автомат|мех|tsi|tdi|tdci|hdi|mpi|fsi|gdi|hybrid|plug|"
    rf"{_FUEL_WORD}"
)


def _normalize_spec_key(key: str) -> str:
    return _APOSTROPHE_RE.sub("'", (key or "").strip().lower())


def _key_is_engine_spec(key: str) -> bool:
    normalized = _normalize_spec_key(key)
    if "об" in normalized and "єм" in normalized:
        return True
    if "объем" in normalized or "обьем" in normalized:
        return True
    if "engine" in normalized and any(token in normalized for token in ("volume", "capacity", "size")):
        return True
    if normalized in {"engine", "motor", "двигун", "мотор"}:
        return True
    return False

_STRUCTURED_KEYS = (
    "engineVolume",
    "engineVolumeLitres",
    "engine_volume",
    "engine_volume_l",
    "volumeLitres",
    "volume",
    "engine",
)


def normalize_engine_litres(raw: float) -> float | None:
    """2.0 л, 1995 см³ або 2000 (куб. см) → літри."""
    if raw <= 0:
        return None
    if raw >= 100:
        return round(raw / 1000.0, 2)
    if raw <= 20:
        return round(raw, 2)
    return None


def _litres_from_token(value: str) -> float | None:
    try:
        return normalize_engine_litres(float(value.replace(",", ".")))
    except (TypeError, ValueError):
        return None


def _parse_structured_value(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return normalize_engine_litres(float(raw))
    if isinstance(raw, str):
        match = re.search(r"([\d]+[.,]?\d*)", raw.replace(" ", ""))
        if match:
            return _litres_from_token(match.group(1))
    if isinstance(raw, dict):
        for sub_key in ("liters", "litres", "value", "l"):
            parsed = _parse_structured_value(raw.get(sub_key))
            if parsed is not None:
                return parsed
    return None


def _from_structured_sources(item: ListingOut) -> float | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}

    for source in (auto, specs, sd):
        for key in _STRUCTURED_KEYS:
            parsed = _parse_structured_value(source.get(key))
            if parsed is not None:
                return parsed

    for source in (specs, auto):
        for spec_key, spec_value in source.items():
            if not _key_is_engine_spec(str(spec_key)):
                continue
            parsed = _parse_structured_value(spec_value)
            if parsed is not None:
                return parsed

    # AUTO.RIA: fuelName = «Бензин, 3 л.» / «Дизель, 2.99 л.» (engineVolume часто None).
    for source in (auto, sd):
        for fuel_key in ("fuelName", "fuel"):
            raw = source.get(fuel_key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            parsed = _from_text(raw)
            if parsed is not None:
                return parsed

    return None


def _from_text(text: str) -> float | None:
    blob = norm_text(text)
    if not blob:
        return None

    for pattern in (
        r"(?:об['ʼ]?єм|двигун|мотор|engine|motor)\s*[:\-]?\s*(\d+[.,]?\d*)",
        # «3.0 л», «2,5 л», «3 л.» (AUTO.RIA fuelName)
        r"(\d+[.,]\d+)\s*(?:л|l|litre|liter|літр)\.?\b",
        r"(\d{1,2})\s*(?:л|l|litre|liter|літр)\.?\b",
        # «бензин 3.0», «Дизель, 2.99» — лише десяткове (не «бензин 2019»)
        rf"(?:{_FUEL_WORD})\s*[,:]?\s*(\d+[.,]\d+)",
        # «бензин, 3 л» / «дизель 3л»
        rf"(?:{_FUEL_WORD})\s*[,:]?\s*(\d{{1,2}})\s*(?:л|l)\.?",
        # «3.0 бензин», «3,0 дизель»
        rf"(\d+[.,]\d+)\s*(?:{_FUEL_WORD})",
        r"(\d{3,4})\s*(?:см3|см³|cc|куб\.?|cm3)\b",
    ):
        match = re.search(pattern, blob, re.I)
        if not match:
            continue
        parsed = _litres_from_token(match.group(1))
        if parsed is not None and 0.6 <= parsed <= 10.0:
            return parsed

    match = re.search(rf"\b(\d+[.,]\d+)\s*(?:{_ENGINE_TRANS_HINT})\b", blob, re.I)
    if match:
        parsed = _litres_from_token(match.group(1))
        if parsed is not None and 0.6 <= parsed <= 10.0:
            return parsed

    # «Camry 2.5», «X5 3.0» — десяткове число перед кінцем рядка або розділювачем.
    match = re.search(r"\b(\d\.\d)\b(?=\s*(?:$|[/|,]|—|-\s))", blob)
    if match:
        parsed = _litres_from_token(match.group(1))
        if parsed is not None and 0.8 <= parsed <= 8.0:
            return parsed

    return None


def parse_engine_volume_from_text(text: str) -> float | None:
    """Публічний парсер обʼєму з довільного тексту (fuelName, опис тощо)."""
    return _from_text(text)


def extract_listing_engine_volume(item: ListingOut) -> float | None:
    if getattr(item, "engine_volume_l", None):
        try:
            volume = float(item.engine_volume_l)
            if volume > 0:
                return round(volume, 2)
        except (TypeError, ValueError):
            pass

    structured = _from_structured_sources(item)
    if structured is not None:
        return structured

    # Поле fuel після split може лишитись «Бензин», але іноді ще містить «Бензин, 3 л».
    fuel = getattr(item, "fuel", None) or ""
    if fuel:
        from_fuel = _from_text(str(fuel))
        if from_fuel is not None:
            return from_fuel

    title = item.title or ""
    description = item.description or ""
    if title:
        from_title = _from_text(title)
        if from_title is not None:
            return from_title

    if description:
        from_description = _from_text(description)
        if from_description is not None:
            return from_description

    combined = f"{title} {description}".strip()
    if combined and combined != title:
        return _from_text(combined)
    return None


def listing_engine_volume_in_range(
    item: ListingOut,
    *,
    volume_from: float | None,
    volume_to: float | None,
) -> bool:
    """True якщо обʼєм невідомий (пропускаємо) або потрапляє в діапазон."""
    if volume_from is None and volume_to is None:
        return True
    engine = extract_listing_engine_volume(item)
    if engine is None:
        return True
    if volume_from is not None and engine < volume_from:
        return False
    if volume_to is not None and engine > volume_to:
        return False
    return True
