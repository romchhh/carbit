from __future__ import annotations

from datetime import datetime

from app.core.timezone import KYIV_TZ, as_kyiv
from app.schemas.schemas import ListingOut


def listing_sort_date(item: ListingOut) -> datetime:
    """Дата для сортування «найновіші»: оновлення (підняття), якщо є, інакше публікація."""
    try:
        refreshed = getattr(item, "refreshed_at", None)
        if refreshed is not None:
            return as_kyiv(refreshed)
        return as_kyiv(item.published_at)
    except Exception:
        return datetime(1970, 1, 1, tzinfo=KYIV_TZ)


__all__ = ["listing_sort_date"]
