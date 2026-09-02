"""Визначення «пригнано з США» для API і пост-фільтрації."""

from __future__ import annotations

from app.core.text import norm_text
from app.schemas.schemas import ListingOut
from app.services.listings.haystack import listing_search_haystack
from app.services.listings.olx_specs import olx_spec_condition_flags

_USA_TOKENS = ("сша", "usa", "america", "штати", "америк", "copart", "iaai")


def _bool_flag(value: object) -> bool | None:
    if value is True or value == 1 or value == "1":
        return True
    if value is False or value == 0 or value == "0":
        return False
    return None


def _auto_ria_page_badges_usa(sd: dict) -> bool | None:
    page_badges = sd.get("ria_page_badges")
    if isinstance(page_badges, dict):
        flag = _bool_flag(page_badges.get("usa_import"))
        if flag is not None:
            return flag
    return None


def _auto_ria_from_usa(sd: dict) -> bool | None:
    page_usa = _auto_ria_page_badges_usa(sd)
    if page_usa is True:
        return True

    for block in (sd, sd.get("autoData"), sd.get("stateData")):
        if not isinstance(block, dict):
            continue
        for key in ("from_usa", "fromUsa", "isFromUsa", "fromUSA"):
            flag = _bool_flag(block.get(key))
            if flag is not None:
                return flag
    badges = sd.get("badges")
    if isinstance(badges, list):
        blob = norm_text(" ".join(str(b) for b in badges))
        if any(token in blob for token in _USA_TOKENS):
            return True
    return None


def _condition_flags_usa(sd: dict) -> bool | None:
    flags = sd.get("condition_flags")
    if not isinstance(flags, dict):
        return None
    if flags.get("usa_import") is True:
        return True
    return None


def extract_listing_usa_import(item: ListingOut) -> bool | None:
    """True — пригнано з США, False — явно ні, None — невідомо."""
    sd = item.source_data if isinstance(item.source_data, dict) else {}

    flags_usa = _condition_flags_usa(sd)
    if flags_usa is True:
        return True

    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}
    olx_flags = olx_spec_condition_flags(specs)
    if olx_flags.get("usa_import"):
        return True

    ar_usa = _auto_ria_from_usa(sd)
    if ar_usa is not None:
        return ar_usa

    haystack = listing_search_haystack(item)
    if not haystack:
        return None

    if any(
        phrase in haystack
        for phrase in ("з сша", "зі сша", "з usa", "з америк", "із сша")
    ):
        return True
    if any(
        phrase in haystack
        for phrase in (
            "пригнан",
            "пригон",
        )
    ) and any(token in haystack for token in _USA_TOKENS):
        return True

    return True if any(token in haystack for token in _USA_TOKENS) else None
