"""Re-export shared currency helpers from backend (single source of truth)."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.currency import (  # noqa: E402
    EUR_TO_UAH,
    USD_TO_UAH,
    convert_price,
    currency_label,
    format_display_price,
    format_price_uah,
    from_uah,
    infer_currency,
    normalize_currency,
    to_uah,
)

__all__ = [
    "USD_TO_UAH",
    "EUR_TO_UAH",
    "normalize_currency",
    "infer_currency",
    "to_uah",
    "from_uah",
    "convert_price",
    "format_display_price",
    "format_price_uah",
    "currency_label",
]
