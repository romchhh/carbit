"""Lazy gallery для AUTO.RIA — повна галерея лише при відкритті картки."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Listing
from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
from app.services.auto_ria.details import extract_image_urls

logger = logging.getLogger(__name__)

# У видачі достатньо cover з photoData (1 URL); повна галерея — на деталях.
GALLERY_COMPLETE_MIN_IMAGES = 2


def auto_ria_needs_gallery(listing: Listing | str, *, images: list[str] | None = None) -> bool:
    listing_id = listing if isinstance(listing, str) else listing.id
    if not listing_id.startswith("auto_ria_"):
        return False
    auto_id = listing_id.removeprefix("auto_ria_")
    if not auto_id.isdigit():
        return False
    imgs = images
    if imgs is None and not isinstance(listing, str):
        imgs = list(listing.images or [])
    return len(imgs or []) < GALLERY_COMPLETE_MIN_IMAGES


async def attach_auto_ria_gallery(db: AsyncSession, listing: Listing) -> list[str]:
    """Тягне /auto/fotos і оновлює Listing.images (якщо є повна галерея)."""
    if not auto_ria_needs_gallery(listing):
        return list(listing.images or [])

    auto_id = listing.id.removeprefix("auto_ria_")
    try:
        client = AutoRiaClient()
        fotos = await client.get_fotos(auto_id)
    except AutoRiaError:
        logger.warning("AUTO.RIA fotos failed for %s", listing.id)
        return list(listing.images or [])
    except Exception:
        logger.exception("AUTO.RIA fotos error for %s", listing.id)
        return list(listing.images or [])

    urls = extract_image_urls({}, fotos)
    if not urls:
        return list(listing.images or [])

    listing.images = urls
    await db.flush()
    return urls
