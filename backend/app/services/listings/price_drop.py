from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.timezone import KYIV_TZ, as_kyiv, now_kyiv
from app.models.models import Listing
from app.services.currency import listing_price_uah

MIN_SIGNIFICANT_PRICE_DROP_PERCENT = 5.0
PRICE_DROP_RECENT_DAYS = 14
PRICE_DROP_NOTIFY_COOLDOWN_DAYS = 7


@dataclass(frozen=True)
class PriceDropInfo:
    previous_price: int
    previous_currency: str
    drop_percent: float
    dropped_at: datetime


def _parse_history_at(raw: object) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return as_kyiv(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return as_kyiv(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def compute_drop_percent(
    old_price: int,
    old_currency: str | None,
    new_price: int,
    new_currency: str | None,
) -> float | None:
    old_uah = listing_price_uah(old_price, old_currency)
    new_uah = listing_price_uah(new_price, new_currency)
    if old_uah <= 0 or new_uah <= 0 or new_uah >= old_uah:
        return None
    return (old_uah - new_uah) / old_uah * 100.0


def is_significant_price_drop(
    old_price: int,
    old_currency: str | None,
    new_price: int,
    new_currency: str | None,
    *,
    min_percent: float = MIN_SIGNIFICANT_PRICE_DROP_PERCENT,
) -> bool:
    drop = compute_drop_percent(old_price, old_currency, new_price, new_currency)
    return drop is not None and drop >= min_percent


def extract_recent_price_drop(
    listing: Listing,
    *,
    min_percent: float = MIN_SIGNIFICANT_PRICE_DROP_PERCENT,
    recent_days: int = PRICE_DROP_RECENT_DAYS,
) -> PriceDropInfo | None:
    history = list(listing.price_history or [])
    if not history:
        return None

    last = history[-1]
    if not isinstance(last, dict):
        return None

    previous_price = last.get("price")
    if previous_price is None:
        return None
    try:
        previous_price = int(previous_price)
    except (TypeError, ValueError):
        return None

    previous_currency = str(last.get("currency") or listing.currency or "USD")
    current_price = int(listing.price or 0)
    current_currency = listing.currency or "USD"

    drop_percent = compute_drop_percent(
        previous_price,
        previous_currency,
        current_price,
        current_currency,
    )
    if drop_percent is None or drop_percent < min_percent:
        return None

    dropped_at = _parse_history_at(last.get("at")) or now_kyiv()
    if dropped_at < now_kyiv() - timedelta(days=max(recent_days, 1)):
        return None

    return PriceDropInfo(
        previous_price=previous_price,
        previous_currency=previous_currency,
        drop_percent=round(drop_percent, 1),
        dropped_at=dropped_at,
    )


def format_drop_percent(percent: float) -> str:
    rounded = round(percent)
    if abs(percent - rounded) < 0.05:
        return str(int(rounded))
    return f"{percent:.1f}".rstrip("0").rstrip(".")
