from __future__ import annotations

import re
from datetime import datetime

from app.core.timezone import KYIV_TZ

_PUBLISHED_RE = re.compile(
    r"(?:Оновлено|Опубліковано)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})",
    re.IGNORECASE,
)

# Плейсхолдер, поки дату не підтягнули зі сторінки оголошення (не now_kyiv()).
REONO_UNKNOWN_PUBLISHED_AT = datetime(1970, 1, 1, 12, 0, tzinfo=KYIV_TZ)


def parse_reono_updated_text(text: str) -> datetime | None:
    """Парсить «Оновлено 19.08.2026» / «Опубліковано …» зі сторінки оголошення REONO."""
    if not text:
        return None
    match = _PUBLISHED_RE.search(text.strip())
    if not match:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))
    try:
        return datetime(year, month, day, 12, 0, tzinfo=KYIV_TZ)
    except ValueError:
        return None
