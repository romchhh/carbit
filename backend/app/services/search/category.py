"""Фільтр категорії авто: всі / вживані / нові / під пригон.

«Нові» = пробіг до 1000 км (включно), каталог AUTO.RIA /new, або uDrive
(там лише нові з салону). AUTO.RIA з пробігом ≤1000 км рахуємо новими
навіть зі старим роком. Інші джерела до 2020 — ні.
Оголошення без пробігу (0/порожньо) не вважаємо новими, якщо немає явних
маркерів на кшталт «з салону» / «без пробігу» — окрім AUTO.RIA, де 0 км
це raceInt=0 (менше тисячі).
"""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

NEW_MILEAGE_MAX_KM = 1000
# Рік-підлога для не-AUTO.RIA джерел. AUTO.RIA з ≤1000 км — будь-який рік.
NEW_YEAR_MIN = 2020

IMPORT_MARKERS = (
    "пригон",
    "пригнан",  # пригнано, пригнаний, пригнana з …
    "під пригон",
    "под пригон",
    "нерозмит",
    "не розмит",
    "не растом",
    "нерастамож",
    "єврономер",
    "еврономер",
    "з єс",
    "з європ",
    "з европ",
    "з сша",
    "з америк",
    "з кореї",
    "з китаю",
    "польща",
    "литва",
    "латвія",
    "грузія",
    "під замовлення",
    "под заказ",
)

# Без голих «новий/нова» — вони є в «майже новий», «нова гума», «новий акумулятор».
_NEW_TEXT_RE = re.compile(
    r"(?<![a-zа-яёіїєґ0-9])("
    r"з\s+салону|"
    r"без\s+проб[іi]гу|"
    r"без\s+пробега|"
    r"0\s*км|"
    r"0\s*km|"
    r"zero\s*km|"
    r"нове\s+авто|"
    r"новое\s+авто|"
    r"новий\s+автомобіль|"
    r"новый\s+автомобиль|"
    r"авто\s+з\s+салону|"
    r"дилерськ\w*\s+нове|"
    r"дилерск\w*\s+новое"
    r")(?![a-zа-яёіїєґ0-9])",
    re.IGNORECASE,
)


def _looks_import(blob: str) -> bool:
    return any(marker in blob for marker in IMPORT_MARKERS)


def _looks_new_text(blob: str) -> bool:
    return bool(_NEW_TEXT_RE.search(blob))


def _is_auto_ria(item: ListingOut) -> bool:
    item_id = str(getattr(item, "id", None) or "")
    source = str(getattr(item, "source", None) or "").strip().lower()
    return source in {"auto_ria", "autoria", "auto.ria"} or item_id.startswith(
        ("auto_ria_", "new_auto_ria_")
    )


def _from_new_catalog(item: ListingOut) -> bool:
    """Джерела, де всі авто нові з салону (не евристика по пробігу)."""
    item_id = str(getattr(item, "id", None) or "")
    if item_id.startswith("new_auto_ria_"):
        return True
    source = str(getattr(item, "source", None) or "").strip().lower()
    if source == "udrive" or item_id.startswith("udrive_"):
        return True
    return False


def _year_too_old_for_new(item: ListingOut) -> bool:
    year = int(item.year or 0)
    if not (0 < year < NEW_YEAR_MIN):
        return False
    mileage = int(getattr(item, "mileage", None) or 0)
    # AUTO.RIA: «до 1000 км» (включно raceInt=0) — нові незалежно від року.
    if _is_auto_ria(item) and mileage <= NEW_MILEAGE_MAX_KM:
        return False
    return True


def listing_from_new_catalog(item: ListingOut) -> bool:
    return _from_new_catalog(item)


def listing_matches_category(item: ListingOut, category: str | None) -> bool:
    key = (category or "all").strip().lower()
    if not key or key == "all":
        return True

    blob = norm_text(f"{item.title} {item.description or ''} {item.region or ''}")
    mileage = int(item.mileage or 0)
    looks_import = _looks_import(blob)
    looks_new_text = _looks_new_text(blob)
    from_new_catalog = _from_new_catalog(item)
    too_old = _year_too_old_for_new(item)
    auto_ria_low_km = _is_auto_ria(item) and mileage <= NEW_MILEAGE_MAX_KM
    # 1..1000 км — однозначно «нові»; 0 км — маркер / каталог / AUTO.RIA raceInt=0.
    looks_new_mileage = 0 < mileage <= NEW_MILEAGE_MAX_KM
    looks_new_zero = mileage == 0 and (
        looks_new_text or from_new_catalog or auto_ria_low_km
    )
    looks_new = (looks_new_mileage or looks_new_zero or from_new_catalog) and not too_old

    if key == "import":
        return looks_import and not from_new_catalog
    if key == "new":
        if too_old:
            return False
        if looks_import and not from_new_catalog:
            return False
        if mileage > NEW_MILEAGE_MAX_KM and not from_new_catalog:
            return False
        return looks_new
    if key == "used":
        if looks_import:
            return False
        if looks_new:
            return False
        return True
    return True
