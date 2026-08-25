from __future__ import annotations

import logging

from app.services.reono.client import get_shared_http_client
from app.services.reono.constants import REONO_BASE_URL
from app.services.reono.errors import ReonoError
from app.services.reono.images import parse_detail_images

logger = logging.getLogger(__name__)


def _normalize_listing_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        raise ReonoError("REONO: порожнє посилання на оголошення")
    if value.startswith("/"):
        value = REONO_BASE_URL + value
    if not value.startswith(f"{REONO_BASE_URL}/"):
        raise ReonoError("REONO: некоректне посилання на оголошення")
    return value


async def fetch_reono_listing_images(url: str) -> list[str]:
    listing_url = _normalize_listing_url(url)
    client = await get_shared_http_client()
    try:
        response = await client.get(listing_url)
    except Exception as exc:
        raise ReonoError(f"REONO: мережева помилка: {exc}") from exc

    if response.status_code == 404:
        return []
    if response.status_code >= 400:
        raise ReonoError(f"REONO: помилка {response.status_code}")

    images = parse_detail_images(response.text)
    if not images:
        logger.debug("REONO detail page has no images: %s", listing_url)
    return images
