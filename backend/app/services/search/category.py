"""Фільтр категорії авто: всі / вживані / нові / під пригон."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

# Сильні маркери «під пригон» / нерозмитнення.
_IMPORT_STRONG = (
    "під пригон",
    "под пригон",
    "на пригон",
    "нерозмит",
    "не розмит",
    "не растом",
    "нерастамож",
    "не растамож",
)

# Слабкі hints походження — лише разом із пригон/нерозмит/єврономер.
_IMPORT_ORIGIN = (
    "з єс",
    "з сша",
    "з америк",
    "з кореї",
    "з китаю",
    "польщ",
    "литв",
    "латві",
    "грузі",
)

_IMPORT_PLATE = (
    "єврономер",
    "еврономер",
)

# Вже розмитнені (не «без розмитнення») — тоді «з ЄС» ≠ «під пригон».
_IMPORT_CLEARED = (
    "вже розмит",
    "розмитнена",
    "розмитнений",
    "розмитнене",
    "розмитнено",
    "повністю розмит",
    "растаможен",
    "растаможена",
    "пройшов розмит",
    "зроблено розмит",
)

# «0 км» окремо: не ловити «9300 км» / «12000 км» через підрядок «0 км».
_ZERO_KM_RE = re.compile(r"(?<!\d)0\s*км\b")

# Короткі «новий/нова/нове» — лише цілі слова (не «інноваційний»).
_NEW_WORD_RE = re.compile(r"(?<![а-яa-z0-9їієґ])(новий|нова|нове)(?![а-яa-z0-9їієґ])")

# Однозначні фрази «нове авто».
_NEW_STRONG = (
    "нове авто",
    "новий автомобіль",
    "нова машина",
    "новий авто",
    "zero km",
)

# М’які маркери — лише при малому пробігу (інакше «як з салону», «нова гума»).
_NEW_SOFT = (
    "з салону",
    "без пробігу",
)

_SOFT_NEW_MAX_KM = 3000
_WORD_NEW_MAX_KM = 5000


def _customs_cleared(blob: str) -> bool:
    if any(marker in blob for marker in _IMPORT_STRONG):
        return False
    if "без розмит" in blob or "ще не розмит" in blob:
        return False
    return any(marker in blob for marker in _IMPORT_CLEARED)


def _looks_import(blob: str) -> bool:
    if any(marker in blob for marker in _IMPORT_STRONG):
        return True

    if "пригон" in blob:
        return True

    cleared = _customs_cleared(blob)
    has_plate = any(m in blob for m in _IMPORT_PLATE)
    has_origin = any(m in blob for m in _IMPORT_ORIGIN)

    if cleared:
        # «З ЄС, уже розмитнена» — звичайний ринок, не «під пригон».
        return False
    if has_plate:
        return True
    # Походження («з ЄС») само по собі замало — багато розмитнених/запчастин.
    if has_origin and any(
        p in blob
        for p in (
            "під замовлення",
            "под заказ",
            "під заказ",
        )
    ):
        return True
    return False


def _looks_new(blob: str, mileage: int) -> bool:
    if mileage <= 1000:
        return True
    if _ZERO_KM_RE.search(blob):
        return True
    if any(marker in blob for marker in _NEW_STRONG):
        return True
    if mileage <= _SOFT_NEW_MAX_KM and any(marker in blob for marker in _NEW_SOFT):
        return True
    if mileage <= _WORD_NEW_MAX_KM and _NEW_WORD_RE.search(blob):
        return True
    return False


def listing_matches_category(item: ListingOut, category: str | None) -> bool:
    key = (category or "all").strip().lower()
    if not key or key == "all":
        return True

    blob = norm_text(f"{item.title} {item.description or ''} {item.region or ''}")
    mileage = int(item.mileage or 0)
    looks_import = _looks_import(blob)
    looks_new = _looks_new(blob, mileage)

    if key == "import":
        return looks_import
    if key == "new":
        if looks_import:
            return False
        return looks_new
    if key == "used":
        if looks_import:
            return False
        if looks_new and mileage <= 1000:
            return False
        return True
    return True
