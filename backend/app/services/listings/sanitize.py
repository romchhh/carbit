from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

from app.schemas.schemas import ListingOut, PaginatedListings

logger = logging.getLogger(__name__)

_DROP_SOURCE_KEYS = frozenset({"_fotos", "vinSvg", "photosData"})


def _is_safe_image_url(url: Any) -> bool:
    """HTTP(S) або локальні telegram-media шляхи (/api/v1/telegram-media/...)."""
    if not isinstance(url, str):
        return False
    value = url.strip()
    if not value:
        return False
    if value.startswith(("http://", "https://")):
        return True
    # Telegram: FileResponse через backend, без публічного CDN
    return value.startswith("/api/v1/telegram-media/")


def json_safe(value: Any, *, depth: int = 0) -> Any:
    """Приводить вкладені значення до JSON-сумісних (інакше FastAPI дає 500 на response_model)."""
    if depth > 14:
        return None
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return None
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            if key in _DROP_SOURCE_KEYS:
                continue
            name = key if isinstance(key, str) else str(key)
            out[name] = json_safe(child, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [json_safe(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, (set, frozenset)):
        return [json_safe(item, depth=depth + 1) for item in list(value)[:200]]
    try:
        return str(value)[:500]
    except Exception:
        return None


def sanitize_listing_out(item: ListingOut) -> ListingOut | None:
    """Гарантує, що оголошення серіалізується в response_model без 500."""
    try:
        data = item.model_dump()
        data["id"] = str(data.get("id") or "")
        data["source"] = str(data.get("source") or "")
        data["title"] = str(data.get("title") or "")
        data["brand"] = str(data.get("brand") or "")
        data["model"] = str(data.get("model") or "")
        data["year"] = int(data.get("year") or 0)
        data["price"] = int(round(float(data.get("price") or 0)))
        data["currency"] = str(data.get("currency") or "USD")
        data["mileage"] = int(data.get("mileage") or 0)
        data["fuel"] = str(data.get("fuel") or "")
        data["transmission"] = str(data.get("transmission") or "")
        if data.get("engine_volume_l") is not None:
            try:
                data["engine_volume_l"] = round(float(data["engine_volume_l"]), 2)
            except (TypeError, ValueError):
                data["engine_volume_l"] = None
        data["region"] = str(data.get("region") or "")
        data["url"] = str(data.get("url") or "")
        data["seller_type"] = str(data.get("seller_type") or "private")
        data["is_duplicate"] = bool(data.get("is_duplicate"))

        images = data.get("images") or []
        data["images"] = [url for url in images if _is_safe_image_url(url)][:30]

        history = data.get("price_history") or []
        data["price_history"] = [row for row in history if isinstance(row, dict)][:50]

        if data.get("source_data") is not None:
            data["source_data"] = json_safe(data["source_data"])

        from app.services.listings.engine_volume import extract_listing_engine_volume

        validated = ListingOut.model_validate(data)
        if validated.engine_volume_l is None:
            volume = extract_listing_engine_volume(validated)
            if volume is not None:
                validated = validated.model_copy(update={"engine_volume_l": volume})
        return validated
    except Exception:
        logger.exception("Dropping listing that failed response sanitize: %s", getattr(item, "id", "?"))
        return None


def sanitize_paginated_listings(results: PaginatedListings) -> PaginatedListings:
    items = [item for item in (sanitize_listing_out(row) for row in results.items) if item is not None]
    return PaginatedListings(
        items=items,
        total=int(results.total or 0),
        market_total=results.market_total,
        page=int(results.page or 1),
        per_page=int(results.per_page or 20),
        pages=int(results.pages or 0),
        sources=list(results.sources or []),
        partial=bool(results.partial),
        from_cache=bool(results.from_cache),
    )


_LIST_SOURCE_KEEP = frozenset(
    {
        "UAH",
        "USD",
        "EUR",
        "prices",
        "published",
        "createdTime",
        "lastRefreshTime",
        "addDate",
        "price_original",
        "price_currency",
        "channel",
        "phone",
    }
)


def slim_source_data_for_list(source_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Менший payload для карток у видачі; повний source_data — лише в деталях."""
    if not source_data:
        return None
    slim: dict[str, Any] = {}
    for key, value in source_data.items():
        if key in _LIST_SOURCE_KEEP or key.startswith("price"):
            slim[key] = value
    return slim or None


def slim_listing_for_list(item: ListingOut) -> ListingOut:
    return item.model_copy(update={"source_data": slim_source_data_for_list(item.source_data)})
