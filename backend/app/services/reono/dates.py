from __future__ import annotations

import re
from datetime import datetime

from app.core.timezone import KYIV_TZ

_UPDATED_RE = re.compile(
    r"Оновлено\s+(\d{1,2})\.(\d{1,2})\.(\d{4})",
    re.IGNORECASE,
)


def parse_reono_updated_text(text: str) -> datetime | None:
    """Парсить «Оновлено 19.08.2026» зі сторінки оголошення REONO."""
    if not text:
        return None
    match = _UPDATED_RE.search(text.strip())
    if not match:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))
    try:
        return datetime(year, month, day, 12, 0, tzinfo=KYIV_TZ)
    except ValueError:
        return None
