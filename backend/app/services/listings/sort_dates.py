from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.timezone import KYIV_TZ, as_kyiv
from app.schemas.schemas import ListingOut

_SENTINEL_YEAR = 1971


def usable_sort_datetime(value: Any) -> datetime | None:
    """Реальна дата для сортування; 1970/порожнє з парсера не рахуємо."""
    if value is None:
        return None
    try:
        dt = as_kyiv(value)
    except Exception:
        return None
    if dt.year <= _SENTINEL_YEAR:
        return None
    return dt


def listing_sort_date(item: ListingOut) -> datetime:
    """«Спочатку нові» — дата публікації, не підняття оголошення."""
    published = usable_sort_datetime(getattr(item, "published_at", None))
    if published is not None:
        return published
    for attr in ("refreshed_at", "found_at"):
        fallback = usable_sort_datetime(getattr(item, attr, None))
        if fallback is not None:
            return fallback
    return datetime(1970, 1, 1, tzinfo=KYIV_TZ)


__all__ = ["listing_sort_date", "usable_sort_datetime"]
