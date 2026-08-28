"""Парсинг публічних URL AUTO.RIA → внутрішній id Carbit."""

from __future__ import annotations

import re

_AUTO_RIA_USED = re.compile(
    r"auto\.ria\.com/(?:uk/)?auto_[^/?#]+_(\d+)\.html",
    re.IGNORECASE,
)
_AUTO_RIA_NEW = re.compile(
    r"auto\.ria\.com/(?:uk/)?(?:newauto/)?auto[-/](\d+)\.html",
    re.IGNORECASE,
)
_TRAILING_ID = re.compile(r"_(\d+)\.html(?:[/?#]|$)", re.IGNORECASE)
# Голі цифри в brand — лише id оголошення (типово 6+ цифр). Моделі на кшталт 001/007/911 — ні.
_MIN_BARE_LISTING_ID_LEN = 6


def parse_auto_ria_url(url: str) -> tuple[str, str] | None:
    """Повертає (auto_id, kind), де kind — ``used`` або ``new``."""
    raw = (url or "").strip()
    if not raw:
        return None

    match = _AUTO_RIA_NEW.search(raw)
    if match:
        return match.group(1), "new"

    match = _AUTO_RIA_USED.search(raw)
    if match:
        return match.group(1), "used"

    match = _TRAILING_ID.search(raw)
    if match:
        return match.group(1), "used"

    return None


def auto_ria_numeric_id_from_text(raw: str, *, allow_short_digits: bool = False) -> str | None:
    """Числовий id оголошення з URL, auto_ria_123 або голого id."""
    value = (raw or "").strip()
    if not value:
        return None
    if value.isdigit():
        if allow_short_digits or len(value) >= _MIN_BARE_LISTING_ID_LEN:
            return value
        return None
    converted = listing_id_from_external_url(value)
    if converted:
        suffix = converted.removeprefix("new_auto_ria_").removeprefix("auto_ria_")
        return suffix if suffix.isdigit() else None
    parsed = parse_auto_ria_url(value)
    if parsed and parsed[0].isdigit():
        return parsed[0]
    return None


def omni_id_from_search_filters(filters) -> str | None:
    """Якщо в brand вставили посилання AUTO.RIA або id оголошення — omni_id пошуку."""
    brand = str(getattr(filters, "brand", None) or "")
    found = auto_ria_numeric_id_from_text(brand, allow_short_digits=False)
    if found:
        return found

    model = str(getattr(filters, "model", None) or "")
    if not model:
        return None
    # У model лише URL / auto_ria_* — не трицифрові коди моделей (001, 911, 500).
    if "auto.ria" in model.lower() or model.lower().startswith("auto_ria_"):
        return auto_ria_numeric_id_from_text(model, allow_short_digits=True)
    return None


def listing_id_matches_omni_search(listing_id: str | None, filters) -> bool:
    """True, якщо пошук був за конкретним id/URL AUTO.RIA і це те саме оголошення."""
    omni_id = omni_id_from_search_filters(filters)
    if not omni_id or not listing_id:
        return False
    raw = str(listing_id).strip()
    if raw.startswith("new_auto_ria_"):
        return raw.removeprefix("new_auto_ria_") == omni_id
    if raw.startswith("auto_ria_"):
        return raw.removeprefix("auto_ria_") == omni_id
    return raw == omni_id


def listing_id_from_external_url(raw: str) -> str | None:
    """AUTO.RIA URL або ``auto_ria_123`` → ``auto_ria_123`` / ``new_auto_ria_123``."""
    value = (raw or "").strip()
    if not value:
        return None

    if value.startswith("new_auto_ria_"):
        suffix = value.removeprefix("new_auto_ria_")
        return value if suffix.isdigit() else None
    if value.startswith("auto_ria_"):
        suffix = value.removeprefix("auto_ria_")
        return value if suffix.isdigit() else None

    parsed = parse_auto_ria_url(value)
    if not parsed:
        return None

    auto_id, kind = parsed
    if not auto_id.isdigit():
        return None
    return f"new_auto_ria_{auto_id}" if kind == "new" else f"auto_ria_{auto_id}"
