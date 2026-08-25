from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.reono.constants import REONO_BASE_URL
from app.services.reono.images import is_reono_cdn_url, reono_fallback_urls

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external-media", tags=["external-media"])

_IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{REONO_BASE_URL}/",
}


@router.get("")
async def proxy_external_media(url: str = Query(..., min_length=8, max_length=4096)):
    """Проксі для CDN REONO — обходить hotlink-захист stx.reono.ua у картках Carbit."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Некоректне посилання")
    if not is_reono_cdn_url(url):
        raise HTTPException(status_code=400, detail="Джерело не підтримується")

    candidates = reono_fallback_urls(url)
    last_exc: Exception | None = None
    last_status = 502

    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers=_IMAGE_HEADERS,
        ) as client:
            for candidate in candidates:
                try:
                    upstream = await client.get(candidate)
                except httpx.HTTPError as exc:
                    last_exc = exc
                    continue
                if upstream.status_code < 400:
                    content_type = upstream.headers.get("content-type") or "image/jpeg"
                    if "image" not in content_type.lower():
                        continue
                    return Response(
                        content=upstream.content,
                        media_type=content_type,
                        headers={
                            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
                        },
                    )
                last_status = upstream.status_code
    except httpx.HTTPError as exc:
        last_exc = exc

    if last_exc is not None:
        logger.warning("external-media fetch failed for %s: %s", url, last_exc)
        raise HTTPException(status_code=502, detail="Не вдалося завантажити фото") from last_exc

    raise HTTPException(status_code=last_status, detail="Фото недоступне")
