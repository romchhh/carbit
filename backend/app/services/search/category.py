"""Фільтр категорії авто: всі / вживані / нові / під пригон.

«Нові» = 2025–2026 рік і пробіг до 1000 км (включно) для AUTO.RIA, OLX тощо.
uDrive — лише нові з салону (будь-який рік/пробіг на платформі).
Каталог AUTO.RIA /new — за правилами 2025–2026 і ≤1000 км.
"""

from __future__ import annotations

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

NEW_MILEAGE_MAX_KM = 1000
NEW_YEAR_MIN = 2025
NEW_YEAR_MAX = 2026

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


def new_category_year_bounds(
    year_from: int | None = None,
    year_to: int | None = None,
) -> tuple[int, int]:
    """Перетин користувацького діапазону року з 2025–2026 для категорії «Нові»."""
    yf = max(int(year_from or 0), NEW_YEAR_MIN) if year_from else NEW_YEAR_MIN
    yt = min(int(year_to or 0), NEW_YEAR_MAX) if year_to else NEW_YEAR_MAX
    if yf > yt:
        return NEW_YEAR_MIN, NEW_YEAR_MAX
    return yf, yt


def _looks_import(blob: str) -> bool:
    return any(marker in blob for marker in IMPORT_MARKERS)


def _is_udrive(item: ListingOut) -> bool:
    item_id = str(getattr(item, "id", None) or "")
    source = str(getattr(item, "source", None) or "").strip().lower()
    return source == "udrive" or item_id.startswith("udrive_")


def _is_new_auto_ria_catalog(item: ListingOut) -> bool:
    return str(getattr(item, "id", None) or "").startswith("new_auto_ria_")


def _from_new_catalog(item: ListingOut) -> bool:
    """Джерела, де всі авто нові з салону."""
    return _is_udrive(item) or _is_new_auto_ria_catalog(item)


def _year_in_new_range(item: ListingOut) -> bool:
    year = int(item.year or 0)
    return NEW_YEAR_MIN <= year <= NEW_YEAR_MAX


def listing_from_new_catalog(item: ListingOut) -> bool:
    return _from_new_catalog(item)


def listing_is_udrive(item: ListingOut) -> bool:
    return _is_udrive(item)


def listing_matches_category(item: ListingOut, category: str | None) -> bool:
    key = (category or "all").strip().lower()
    if not key or key == "all":
        return True

    if _is_udrive(item):
        if key == "import":
            return False
        if key == "used":
            return False
        return True

    blob = norm_text(f"{item.title} {item.description or ''} {item.region or ''}")
    mileage = int(item.mileage or 0)
    looks_import = _looks_import(blob)
    from_new_catalog = _from_new_catalog(item)
    year_ok = _year_in_new_range(item)
    mileage_ok = mileage <= NEW_MILEAGE_MAX_KM
    looks_new = year_ok and mileage_ok and (not looks_import or from_new_catalog)

    if key == "import":
        return looks_import and not from_new_catalog
    if key == "new":
        return looks_new
    if key == "used":
        if looks_import:
            return False
        if looks_new:
            return False
        return True
    return True
