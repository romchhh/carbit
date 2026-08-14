"""Фільтр категорії авто: всі / вживані / нові / під пригон.

«Нові» = пробіг до 1000 км (включно).
Оголошення без пробігу (0/порожньо) не вважаємо новими, якщо немає явних
маркерів на кшталт «з салону» / «без пробігу» — інакше в «Нові» потрапляє
весь вживаний парк із нерозпарсеним mileage.
"""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

NEW_MILEAGE_MAX_KM = 1000

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


def listing_matches_category(item: ListingOut, category: str | None) -> bool:
    key = (category or "all").strip().lower()
    if not key or key == "all":
        return True

    blob = norm_text(f"{item.title} {item.description or ''} {item.region or ''}")
    mileage = int(item.mileage or 0)
    looks_import = _looks_import(blob)
    looks_new_text = _looks_new_text(blob)
    # 1..1000 км — однозначно «нові»; 0 км — лише з явним маркером (або справді нуль).
    looks_new_mileage = 0 < mileage <= NEW_MILEAGE_MAX_KM
    looks_new_zero = mileage == 0 and looks_new_text
    looks_new = looks_new_mileage or looks_new_zero

    if key == "import":
        return looks_import
    if key == "new":
        if looks_import:
            return False
        if mileage > NEW_MILEAGE_MAX_KM:
            return False
        return looks_new
    if key == "used":
        if looks_import:
            return False
        if looks_new:
            return False
        return True
    return True
