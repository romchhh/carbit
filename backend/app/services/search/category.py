"""Фільтр категорії авто: всі / вживані / нові / під пригон."""

from __future__ import annotations

from app.core.text import norm_text
from app.schemas.schemas import ListingOut

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

NEW_MARKERS = (
    "новий",
    "нова",
    "нове авто",
    "з салону",
    "без пробігу",
    "0 км",
    "0км",
    "zero km",
)


def listing_matches_category(item: ListingOut, category: str | None) -> bool:
    key = (category or "all").strip().lower()
    if not key or key == "all":
        return True

    blob = norm_text(f"{item.title} {item.description or ''} {item.region or ''}")
    mileage = int(item.mileage or 0)
    looks_import = any(marker in blob for marker in IMPORT_MARKERS)
    looks_new = mileage <= 1000 or any(marker in blob for marker in NEW_MARKERS)

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
