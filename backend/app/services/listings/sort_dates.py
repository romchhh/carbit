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


def coalesce_listing_published_at(
    published_at: datetime | None,
    *,
    refreshed_at: datetime | None = None,
    found_at: datetime | None = None,
) -> datetime:
    """Для API/UI: placeholder 1970 з парсера не показуємо клієнту."""
    from app.core.timezone import now_kyiv

    for candidate in (published_at, refreshed_at, found_at):
        usable = usable_sort_datetime(candidate)
        if usable is not None:
            return usable
    return now_kyiv()


__all__ = ["coalesce_listing_published_at", "listing_sort_date", "usable_sort_datetime"]
