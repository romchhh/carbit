"""Свіжість оголошень у пошуку (за замовчуванням ≤ 4 місяці)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import settings
from app.core.timezone import as_kyiv, now_kyiv


def listing_max_age_days() -> int:
    """Строк зберігання; читаємо щоразу, щоб LISTING_MAX_AGE_DAYS діяв без релізу."""
    try:
        return max(1, int(settings.LISTING_MAX_AGE_DAYS))
    except (TypeError, ValueError):
        return 120


# Історична назва: імпортується в media_cleanup / purge / тестах.
TELEGRAM_LISTING_MAX_AGE_DAYS = listing_max_age_days()


def telegram_published_cutoff() -> datetime:
    return now_kyiv() - timedelta(days=listing_max_age_days())


def telegram_listing_is_fresh(
    published_at: datetime | None,
    *,
    found_at: datetime | None = None,
) -> bool:
    """True якщо оголошення не старше строку зберігання.

    Без published_at не блокуємо (SQL/скан уже ріжуть за датою поста).
    found_at не використовується — важлива дата публікації в Telegram.
    """
    del found_at  # API-сумісність; свіжість = дата поста, не індексації
    if published_at is None:
        return True
    try:
        return as_kyiv(published_at) >= telegram_published_cutoff()
    except Exception:
        return True
