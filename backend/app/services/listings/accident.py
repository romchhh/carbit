"""Визначення участі авто в ДТП для пост-фільтрації."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

_CYR_BOUNDARY_START = r"(?:^|(?<![\wа-яіїєґ]))"
_CYR_BOUNDARY_END = r"(?:$|(?![\wа-яіїєґ]))"

_ACCIDENT_HAD_TEXT = re.compile(
    _CYR_BOUNDARY_START
    + r"(дтп|accident|after crash|після дтп|був у дтп|був в дтп|after an accident|"
    + r"легкий удар|сильний удар|після удару|був удар|"
    + r"бита|битий|битая|биті|"
    + r"після аварії|була в аварії)"
    + _CYR_BOUNDARY_END,
    re.IGNORECASE,
)
_ACCIDENT_NONE_TEXT = re.compile(
    _CYR_BOUNDARY_START
    + r"(без дтп|не в дтп|не був у дтп|не був в дтп|дтп не був|дтп небув|"
    + r"в дтп не був|в дтп небув|no accident|not damaged|не бита|не бит)"
    + _CYR_BOUNDARY_END,
    re.IGNORECASE,
)


def _imperiya_was_accident(imperiya: dict) -> bool | None:
    if imperiya.get("wasAccident") is not None:
        return bool(imperiya.get("wasAccident"))
    condition = imperiya.get("condition")
    if isinstance(condition, dict) and condition.get("wasAccident") is not None:
        return bool(condition.get("wasAccident"))
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


def extract_listing_accident_had(item: ListingOut) -> bool | None:
    """True — був у ДТП, False — явно не був, None — невідомо."""
    sd = item.source_data if isinstance(item.source_data, dict) else {}

    imperiya = sd.get("imperiya")
    if isinstance(imperiya, dict):
        had = _imperiya_was_accident(imperiya)
        if had is not None:
            return had

    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    damage_raw = auto.get("damageId", auto.get("damage"))
    if damage_raw is not None:
        try:
            damage_id = int(damage_raw)
        except (TypeError, ValueError):
            damage_id = None
        if damage_id == 1:
            return False
        if damage_id == 2:
            return True

    damage_name = norm_text(str(auto.get("damageName") or ""))
    if damage_name:
        if any(token in damage_name for token in ("не був", "not in", "без дтп", "not damaged")):
            return False
        if any(token in damage_name for token in ("був", "після", "after", "дтп", "accident")):
            return True

    haystack = _listing_haystack(item)
    if _ACCIDENT_NONE_TEXT.search(haystack):
        return False
    if _ACCIDENT_HAD_TEXT.search(haystack):
        return True
    return None


def listing_matches_accident_filter(item: ListingOut, accident: str | None) -> bool:
    """Перевірка фільтра ДТП з урахуванням особливостей джерел."""
    if not accident:
        return True

    value = accident.strip().lower()
    if value not in {"none", "had"}:
        return True

    source = (item.source or "").strip().lower()
    had = extract_listing_accident_had(item)

    # AUTO.RIA: damage=1/2 у search API + пост-фільтр по опису / damageName.
    if source == "auto_ria":
        if value == "none":
            return had is not True
        if value == "had":
            return had is not False
        return True

    if value == "none":
        return had is not True
    return had is True
