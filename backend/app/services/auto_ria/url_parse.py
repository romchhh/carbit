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

# Голі цифри — лише id оголошення (типово 6+). Моделі 001/007/911/3/500 — ні.
_MIN_USED_LISTING_ID_LEN = 6
_MIN_NEW_LISTING_ID_LEN = 5
# Чисто цифрові коди ≤4 символів — завжди модель, не id оголошення.
_MAX_NUMERIC_MODEL_CODE_LEN = 4

_AUTO_RIA_REF_PREFIXES = ("auto_ria_", "new_auto_ria_")


def is_likely_numeric_model_code(value: str) -> bool:
    """Чи схоже значення на код моделі (001, 911, 3), а не на id оголошення."""
    text = (value or "").strip()
    if not text or not text.isdigit():
        return False
    return len(text) <= _MAX_NUMERIC_MODEL_CODE_LEN


def _min_id_len_for_kind(kind: str) -> int:
    return _MIN_NEW_LISTING_ID_LEN if kind == "new" else _MIN_USED_LISTING_ID_LEN


def _suffix_is_valid_listing_id(suffix: str, *, kind: str = "used") -> bool:
    return suffix.isdigit() and len(suffix) >= _min_id_len_for_kind(kind)


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


def _is_auto_ria_reference_text(value: str) -> bool:
    low = (value or "").strip().lower()
    if not low:
        return False
    if "auto.ria" in low:
        return True
    return low.startswith(_AUTO_RIA_REF_PREFIXES)


def extract_numeric_listing_id(raw: str) -> str | None:
    """Id оголошення з URL, auto_ria_* / new_auto_ria_* або голих цифр (6+)."""
    value = (raw or "").strip()
    if not value:
        return None

    low = value.lower()
    if low.startswith("new_auto_ria_"):
        suffix = value[len("new_auto_ria_") :]
        return suffix if _suffix_is_valid_listing_id(suffix, kind="new") else None

    if low.startswith("auto_ria_"):
        suffix = value[len("auto_ria_") :]
        return suffix if _suffix_is_valid_listing_id(suffix, kind="used") else None

    if value.isdigit():
        if is_likely_numeric_model_code(value):
            return None
        return value if _suffix_is_valid_listing_id(value, kind="used") else None

    parsed = parse_auto_ria_url(value)
    if parsed:
        auto_id, kind = parsed
        if _suffix_is_valid_listing_id(auto_id, kind=kind):
            return auto_id
        return None

    converted = listing_id_from_external_url(value)
    if converted:
        if converted.startswith("new_auto_ria_"):
            suffix = converted.removeprefix("new_auto_ria_")
            return suffix if _suffix_is_valid_listing_id(suffix, kind="new") else None
        suffix = converted.removeprefix("auto_ria_")
        return suffix if _suffix_is_valid_listing_id(suffix, kind="used") else None

    return None


def _model_codes_equivalent(left: str, right: str) -> bool:
    a = (left or "").strip()
    b = (right or "").strip()
    if not a or not b:
        return False
    if a.lower() == b.lower():
        return True
    if a.isdigit() and b.isdigit():
        return a.lstrip("0") == b.lstrip("0") or int(a) == int(b)
    return False


def _omni_conflicts_with_model_filters(omni_id: str, filters) -> bool:
    """Не шукати omni_id, якщо він збігається з обраною моделлю (001, 911…)."""
    from app.services.search.filter_multi import effective_models

    if is_likely_numeric_model_code(omni_id):
        return True
    for model in effective_models(filters):
        if _model_codes_equivalent(omni_id, model):
            return True
    return False


def _finalize_omni_id(omni_id: str | None, filters) -> str | None:
    if not omni_id:
        return None
    if _omni_conflicts_with_model_filters(omni_id, filters):
        return None
    return omni_id


def omni_id_from_search_filters(filters) -> str | None:
    """Посилання / id оголошення в brand(s) або URL у model(s) → omni_id пошуку."""
    from app.services.search.filter_multi import effective_brands, effective_models

    for brand in effective_brands(filters):
        found = extract_numeric_listing_id(brand)
        finalized = _finalize_omni_id(found, filters)
        if finalized:
            return finalized

    for model in effective_models(filters):
        text = (model or "").strip()
        if not text or not _is_auto_ria_reference_text(text):
            continue
        found = extract_numeric_listing_id(text)
        finalized = _finalize_omni_id(found, filters)
        if finalized:
            return finalized

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

    low = value.lower()
    if low.startswith("new_auto_ria_"):
        suffix = value[len("new_auto_ria_") :]
        if _suffix_is_valid_listing_id(suffix, kind="new"):
            return f"new_auto_ria_{suffix}"
        return None

    if low.startswith("auto_ria_"):
        suffix = value[len("auto_ria_") :]
        if _suffix_is_valid_listing_id(suffix, kind="used"):
            return f"auto_ria_{suffix}"
        return None

    parsed = parse_auto_ria_url(value)
    if not parsed:
        return None

    auto_id, kind = parsed
    if not _suffix_is_valid_listing_id(auto_id, kind=kind):
        return None
    return f"new_auto_ria_{auto_id}" if kind == "new" else f"auto_ria_{auto_id}"


# Зворотна сумісність для тестів / зовнішніх імпортів.
def auto_ria_numeric_id_from_text(raw: str, *, allow_short_digits: bool = False) -> str | None:
    del allow_short_digits  # застарілий прапорець; логіка в extract_numeric_listing_id
    return extract_numeric_listing_id(raw)
