"""Визначення участі авто в ДТП для пост-фільтрації."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut, SearchFilters

_CYR_BOUNDARY_START = r"(?:^|(?<![\wа-яіїєґ]))"
_CYR_BOUNDARY_END = r"(?:$|(?![\wа-яіїєґ]))"

_ACCIDENT_HAD_TEXT = re.compile(
    _CYR_BOUNDARY_START
    + r"(дтп|accident|after crash|після дтп|був у дтп|був в дтп|after an accident|"
    + r"легкий удар|сильний удар|після удару|був удар|"
    + r"бита|битий|битая|биті|биток|"
    + r"крашен[аийоїє]?|"
    + r"потребує ремонту|требует ремонта|"
    + r"аварійн[аийоїє]?|аварийн[аыйой]?|"
    + r"після аварії|була в аварії|"
    + r"salvage|rebuilt title)"
    + _CYR_BOUNDARY_END,
    re.IGNORECASE,
)
_ACCIDENT_NONE_TEXT = re.compile(
    _CYR_BOUNDARY_START
    + r"(без дтп|не в дтп|не був у дтп|не був в дтп|дтп не був|дтп небув|"
    + r"в дтп не був|в дтп небув|no accident|not damaged|"
    + r"не бита|не бит|не битий|не битая|"
    + r"не крашена|не крашен|не аварійна|не аварийна)"
    + _CYR_BOUNDARY_END,
    re.IGNORECASE,
)

# Фрази з parser/extractor.py — substring, перевіряємо після «не бита»-маркерів.
_DAMAGED_PHRASES = (
    "після дтп",
    "потребує ремонту",
    "требует ремонта",
    "after accident",
    "легкий удар",
    "сильний удар",
)


def accident_filter_active(filters: SearchFilters | None) -> bool:
    if not filters or not filters.accident:
        return False
    return filters.accident.strip().lower() in {"none", "had"}


def search_needs_olx_detail_enrich(filters: SearchFilters | None) -> bool:
    """OLX-картки в каталозі часто без опису — для фільтра ДТП треба деталі."""
    return accident_filter_active(filters)


def _imperiya_was_accident(imperiya: dict) -> bool | None:
    if imperiya.get("wasAccident") is not None:
        return bool(imperiya.get("wasAccident"))
    condition = imperiya.get("condition")
    if isinstance(condition, dict) and condition.get("wasAccident") is not None:
        return bool(condition.get("wasAccident"))
    return None


def _condition_flags_had(sd: dict) -> bool | None:
    flags = sd.get("condition_flags")
    if not isinstance(flags, dict):
        return None
    if flags.get("damaged") is True:
        return True
    if flags.get("not_damaged") is True:
        return False
    for key in ("accident", "had_accident", "dtp"):
        if flags.get(key) is True:
            return True
        if flags.get(key) is False:
            return False
    return None


def _auto_ria_damage_fields(sd: dict) -> tuple[object | None, str]:
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    state = sd.get("stateData") if isinstance(sd.get("stateData"), dict) else {}

    damage_raw = None
    for block in (auto, state, sd):
        if not isinstance(block, dict):
            continue
        raw = block.get("damageId", block.get("damage"))
        if raw is not None and raw != "":
            damage_raw = raw
            break

    damage_name = ""
    for block in (auto, state, sd):
        if not isinstance(block, dict):
            continue
        name = str(block.get("damageName") or block.get("damage_name") or "").strip()
        if name:
            damage_name = norm_text(name)
            break

    return damage_raw, damage_name


def _damage_id_to_had(damage_raw: object | None) -> bool | None:
    if damage_raw is None or damage_raw == "":
        return None
    try:
        damage_id = int(damage_raw)
    except (TypeError, ValueError):
        return None
    if damage_id == 1:
        return False
    if damage_id == 2:
        return True
    return None


def _damage_name_to_had(damage_name: str) -> bool | None:
    if not damage_name:
        return None
    if any(token in damage_name for token in ("не був", "not in", "без дтп", "not damaged")):
        return False
    if any(token in damage_name for token in ("був", "після", "after", "дтп", "accident")):
        return True
    return None


def _listing_haystack(item: ListingOut) -> str:
    return norm_text(
        " ".join(
            part
            for part in (
                item.title,
                item.description or "",
                item.brand,
                item.model,
            )
            if part
        )
    )


def _text_had_from_haystack(haystack: str) -> bool | None:
    if not haystack:
        return None
    if _ACCIDENT_NONE_TEXT.search(haystack):
        return False
    if _ACCIDENT_HAD_TEXT.search(haystack):
        return True
    low = haystack.lower()
    for phrase in _DAMAGED_PHRASES:
        if phrase in low:
            return True
    # «бита»/«битий» без «не » перед ними
    for token in ("бита", "битий", "битая", "биток", "крашена", "крашен", "аварійна", "аварийна"):
        if token in low and f"не {token}" not in low and f"не{token}" not in low:
            return True
    return None


def extract_listing_accident_had(item: ListingOut) -> bool | None:
    """True — був у ДТП, False — явно не був, None — невідомо."""
    sd = item.source_data if isinstance(item.source_data, dict) else {}

    flags_had = _condition_flags_had(sd)
    if flags_had is not None:
        return flags_had

    imperiya = sd.get("imperiya")
    if isinstance(imperiya, dict):
        had = _imperiya_was_accident(imperiya)
        if had is not None:
            return had

    damage_raw, damage_name = _auto_ria_damage_fields(sd)
    had = _damage_id_to_had(damage_raw)
    if had is not None:
        return had

    had = _damage_name_to_had(damage_name)
    if had is not None:
        return had

    return _text_had_from_haystack(_listing_haystack(item))


def listing_matches_accident_filter(item: ListingOut, accident: str | None) -> bool:
    """Перевірка фільтра ДТП з урахуванням особливостей джерел."""
    if not accident:
        return True

    value = accident.strip().lower()
    if value not in {"none", "had"}:
        return True

    had = extract_listing_accident_had(item)

    if value == "none":
        return had is not True

    # «Був у ДТП»: AUTO.RIA вже фільтрує damage=2, дозволяємо невідомих.
    source = (item.source or "").strip().lower()
    if source == "auto_ria":
        return had is not False
    return had is True
