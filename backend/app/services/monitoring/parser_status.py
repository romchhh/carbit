from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.core.redis import get_redis
from app.services.monitoring.catalog import SOURCE_ALIASES

logger = logging.getLogger(__name__)

_PREFIX = "monitor:parser:"


def normalize_parser_source(name: str) -> str | None:
    key = (name or "").strip().lower().replace("-", "_")
    if key in SOURCE_ALIASES:
        return SOURCE_ALIASES[key]
    compact = key.replace(" ", "").replace(".", "")
    for alias, canonical in SOURCE_ALIASES.items():
        if alias.replace(" ", "").replace(".", "") == compact:
            return canonical
    from app.services.monitoring.catalog import PARSER_LABELS

    for canonical, label in PARSER_LABELS.items():
        if key == label.lower() or compact == label.lower().replace(" ", ""):
            return canonical
    return None


def is_benign_parser_error(error: str | None) -> bool:
    """Помилки, які не означають «парсер мертвий» (порожня видача, невірний шлях)."""
    if not error:
        return False
    err = error.strip().lower()
    if "404" in err:
        return True
    if "not found" in err:
        return True
    if "не знайдено" in err:
        return True
    return False


def is_transient_partial_source_error(error: str | None) -> bool:
    """Тимчасові збої зовнішнього API — не слати адмін-алерт при частковій видачі."""
    if not error:
        return False
    err = error.strip().lower()
    if "cancellederror" in err or err == "cancelled":
        return True
    if "таймаут" in err or "timeout" in err:
        return True
    if "522" in err or "cloudflare" in err:
        return True
    if any(code in err for code in ("502", "503", "504", "429")):
        return True
    if "мережева помилка" in err or "network" in err:
        return True
    if "403" in err or "заблок" in err or "blocked" in err:
        return True
    return False


async def record_parser_status(
    source: str,
    *,
    ok: bool,
    error: str | None = None,
    count: int = 0,
) -> None:
    canonical = normalize_parser_source(source) or source.strip().lower()
    if not canonical:
        return
    payload = {
        "ok": ok,
        "error": (error or "")[:500] or None,
        "count": int(count),
        "at": time.time(),
        "source": canonical,
    }
    try:
        redis = await get_redis()
        await redis.setex(f"{_PREFIX}{canonical}", 86400 * 3, json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.debug("Failed to record parser status for %s", canonical, exc_info=True)


async def get_parser_status(source: str) -> dict[str, Any] | None:
    canonical = normalize_parser_source(source) or source
    try:
        redis = await get_redis()
        raw = await redis.get(f"{_PREFIX}{canonical}")
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("Failed to read parser status for %s", canonical, exc_info=True)
        return None
