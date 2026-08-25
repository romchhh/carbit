"""Підвантаження повної галереї та контактів продавця для live-пошуку (без БД)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
from app.services.auto_ria.details import extract_image_urls
from app.services.auto_ria.mapper import _new_auto_photo_urls
from app.services.imperiya.client import ImperiyaClient
from app.services.imperiya.errors import ImperiyaError
from app.services.imperiya.mapper import _extract_images as imperiya_extract_images
from app.services.listings.seller_contact import (
    extract_phone_from_text,
    merge_seller_contact,
    seller_contact_from_auto_ria,
    seller_contact_from_imperiya,
    seller_contact_from_olx_details,
)
from app.services.olx.client import OlxClient
from app.services.olx.mapper import _listing_images

logger = logging.getLogger(__name__)

GALLERY_COMPLETE_MIN_IMAGES = 2
_SUPPORTED = frozenset({"auto_ria", "olx", "imperiya"})

_AUTO_RIA_ID_RE = re.compile(r"^auto_ria_(\d+)$")
_OLX_ID_RE = re.compile(r"^olx_(.+)$")
_IMPERIYA_ID_RE = re.compile(r"^imperiya_(\d+)$")


@dataclass
class GalleryFetchResult:
    images: list[str]
    seller_name: str | None = None
    seller_phone: str | None = None
    seller_telegram: str | None = None
    seller_url: str | None = None


def gallery_needs_fetch(source: str, images: list[str] | None) -> bool:
    key = (source or "").strip().lower()
    if key not in _SUPPORTED:
        return False
    return len(images or []) < GALLERY_COMPLETE_MIN_IMAGES


def _contact_from_dict(contact: dict[str, str | None]) -> dict[str, str | None]:
    return {k: v for k, v in contact.items() if v}


async def fetch_auto_ria_gallery(
    *,
    listing_id: str | None,
    url: str | None,
    current_images: list[str] | None = None,
) -> GalleryFetchResult:
    match = _AUTO_RIA_ID_RE.match(listing_id or "")
    auto_id = match.group(1) if match else None
    images = list(current_images or [])
    contact: dict[str, str | None] = {}

    try:
        client = AutoRiaClient()
        if auto_id:
            try:
                fotos = await client.get_fotos(auto_id)
                fetched = extract_image_urls({}, fotos)
                if fetched:
                    images = fetched
            except AutoRiaError:
                logger.debug("AUTO.RIA fotos failed for %s", auto_id, exc_info=True)

            try:
                info = await client.get_info(auto_id)
                contact = merge_seller_contact(contact, seller_contact_from_auto_ria(info))
                if len(images) < GALLERY_COMPLETE_MIN_IMAGES:
                    info_images = extract_image_urls(info, None)
                    if info_images:
                        images = info_images
                    photos = info.get("photos")
                    if isinstance(photos, list) and len(images) < GALLERY_COMPLETE_MIN_IMAGES:
                        new_urls = _new_auto_photo_urls(photos)
                        if new_urls:
                            images = new_urls
            except AutoRiaError:
                logger.debug("AUTO.RIA info failed for %s", auto_id, exc_info=True)
    except Exception:
        logger.exception("AUTO.RIA gallery fetch error for %s", listing_id)

    return GalleryFetchResult(images=images, **_contact_from_dict(contact))


async def fetch_olx_gallery(
    *,
    listing_id: str | None,
    url: str | None,
    current_images: list[str] | None = None,
) -> GalleryFetchResult:
    match = _OLX_ID_RE.match(listing_id or "")
    offer_id = match.group(1) if match else None
    images = list(current_images or [])
    contact: dict[str, str | None] = {}

    client = OlxClient()
    listing = None
    if offer_id:
        try:
            listing = await client.fetch_offer_by_id(offer_id)
            if listing:
                api_images = _listing_images(listing)
                if api_images:
                    images = api_images
        except Exception:
            logger.debug("OLX offer fetch failed for %s", offer_id, exc_info=True)

    target_url = (url or "").strip() or (listing.url if listing else "")
    if target_url:
        try:
            details = await client.fetch_listing_details(target_url)
            detail_images = [img for img in details.get("photos") or [] if isinstance(img, str)]
            if detail_images:
                images = detail_images
            contact = merge_seller_contact(
                contact,
                seller_contact_from_olx_details(details),
            )
            if not contact.get("seller_phone"):
                phone = extract_phone_from_text(details.get("description"))
                if phone:
                    contact["seller_phone"] = phone
        except Exception:
            logger.debug("OLX detail fetch failed for %s", target_url, exc_info=True)

    return GalleryFetchResult(images=images, **_contact_from_dict(contact))


async def fetch_imperiya_gallery(
    *,
    listing_id: str | None,
    url: str | None,
    current_images: list[str] | None = None,
) -> GalleryFetchResult:
    match = _IMPERIYA_ID_RE.match(listing_id or "")
    ad_id = match.group(1) if match else None
    images = list(current_images or [])
    contact: dict[str, str | None] = {}

    if not ad_id:
        return GalleryFetchResult(images=images)

    try:
        client = ImperiyaClient()
        ad = await client.get_car(ad_id)
        detail_images = imperiya_extract_images(ad)
        if detail_images:
            images = detail_images
        contact = merge_seller_contact(contact, seller_contact_from_imperiya(ad))
        if not contact.get("seller_phone"):
            phone = extract_phone_from_text(ad.get("description") if isinstance(ad.get("description"), str) else None)
            if phone:
                contact["seller_phone"] = phone
    except ImperiyaError:
        logger.debug("Imperiya get_car failed for %s", ad_id, exc_info=True)
    except Exception:
        logger.exception("Imperiya gallery fetch error for %s", listing_id)

    return GalleryFetchResult(images=images, **_contact_from_dict(contact))


async def fetch_listing_gallery(
    source: str,
    *,
    listing_id: str | None = None,
    url: str | None = None,
    images: list[str] | None = None,
) -> GalleryFetchResult:
    key = (source or "").strip().lower()
    if key == "auto_ria":
        return await fetch_auto_ria_gallery(listing_id=listing_id, url=url, current_images=images)
    if key == "olx":
        return await fetch_olx_gallery(listing_id=listing_id, url=url, current_images=images)
    if key == "imperiya":
        return await fetch_imperiya_gallery(listing_id=listing_id, url=url, current_images=images)
    return GalleryFetchResult(images=list(images or []))
