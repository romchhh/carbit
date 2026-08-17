from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.core.redis import get_redis
from app.schemas.schemas import VinAuctionLinksOut, VinAuctionOut, VinAuctionPhotoOut
from app.services.autohelperbot.errors import AutohelperbotError, AutohelperbotNotFound
from app.services.autohelperbot.scraper import scrape_vin_auction

logger = logging.getLogger(__name__)

CACHE_HIT_TTL = 60 * 60 * 24 * 7
CACHE_MISS_TTL = 60 * 60 * 12
CACHE_PREFIX = "vin:auction:v3:"
MISSING_MARKER = {"_missing": True}


def map_auction_payload(raw: dict[str, Any], *, vin: str) -> VinAuctionOut:
    specs = raw.get("specs") if isinstance(raw.get("specs"), dict) else {}
    photos_raw = raw.get("photos") if isinstance(raw.get("photos"), list) else []
    photos: list[VinAuctionPhotoOut] = []
    for item in photos_raw:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url.startswith("http"):
            photos.append(
                VinAuctionPhotoOut(
                    url=url,
                    caption=item.get("caption") if isinstance(item.get("caption"), str) else None,
                )
            )

    page_url = raw.get("page_url") if isinstance(raw.get("page_url"), str) else None
    title = raw.get("title") if isinstance(raw.get("title"), str) else None
    og_image = raw.get("og_image") if isinstance(raw.get("og_image"), str) else None
    links_raw = raw.get("links") if isinstance(raw.get("links"), dict) else {}
    links = VinAuctionLinksOut(
        carhistory=links_raw.get("carhistory") if isinstance(links_raw.get("carhistory"), str) else None,
        autocheck=links_raw.get("autocheck") if isinstance(links_raw.get("autocheck"), str) else None,
        window_sticker=(
            links_raw.get("window_sticker")
            if isinstance(links_raw.get("window_sticker"), str)
            else None
        ),
        copart=(
            links_raw.get("copart")
            if isinstance(links_raw.get("copart"), str)
            else (raw.get("copart_url") if isinstance(raw.get("copart_url"), str) else None)
        ),
        iaai=(
            links_raw.get("iaai")
            if isinstance(links_raw.get("iaai"), str)
            else (raw.get("iaai_url") if isinstance(raw.get("iaai_url"), str) else None)
        ),
    )

    return VinAuctionOut(
        title=title,
        page_url=page_url,
        lot_id=raw.get("lot_id") if isinstance(raw.get("lot_id"), str) else None,
        copart_url=raw.get("copart_url") if isinstance(raw.get("copart_url"), str) else links.copart,
        iaai_url=raw.get("iaai_url") if isinstance(raw.get("iaai_url"), str) else links.iaai,
        mileage=specs.get("mileage"),
        mileage_km=specs.get("mileage_km"),
        sale_date=specs.get("sale_date"),
        sale_price=specs.get("sale_price"),
        sale_records=specs.get("sale_records"),
        engine=specs.get("engine"),
        color=specs.get("color"),
        transmission=specs.get("transmission"),
        fuel=specs.get("fuel"),
        drive=specs.get("drive"),
        keys=specs.get("keys"),
        repair_cost=specs.get("repair_cost"),
        market_value=specs.get("market_value"),
        primary_damage=specs.get("primary_damage"),
        primary_damage_en=specs.get("primary_damage_en"),
        exterior_condition=specs.get("exterior_condition"),
        avg_price=specs.get("avg_price"),
        meta_description=(
            raw.get("meta_description")
            if isinstance(raw.get("meta_description"), str)
            else None
        ),
        photo_url=photos[0].url if photos else og_image,
        photos=photos,
        links=links,
        source="autohelperbot",
        vin=(raw.get("vin") if isinstance(raw.get("vin"), str) else vin).upper(),
    )


def _cache_key(vin: str) -> str:
    return f"{CACHE_PREFIX}{vin}"


async def lookup_vin_auction(vin: str) -> VinAuctionOut | None:
    """Повертає аукціонні дані або None (не знайдено / вимкнено / помилка)."""
    if not settings.VIN_AUCTION_CHECK_ENABLED:
        return None

    try:
        redis = await get_redis()
        cached = await redis.get(_cache_key(vin))
        if cached:
            data = json.loads(cached)
            if isinstance(data, dict):
                if data.get("_missing"):
                    return None
                return VinAuctionOut.model_validate(data)
    except Exception:
        logger.exception("VIN auction cache read failed")

    try:
        raw = await scrape_vin_auction(vin, headed=False)
        result = map_auction_payload(raw, vin=vin)
    except AutohelperbotNotFound:
        try:
            redis = await get_redis()
            await redis.setex(_cache_key(vin), CACHE_MISS_TTL, json.dumps(MISSING_MARKER))
        except Exception:
            logger.exception("VIN auction miss cache write failed")
        return None
    except AutohelperbotError as exc:
        logger.warning("VIN auction lookup failed for %s: %s", vin, exc.message)
        return None
    except Exception:
        logger.exception("VIN auction unexpected error for %s", vin)
        return None

    try:
        redis = await get_redis()
        await redis.setex(_cache_key(vin), CACHE_HIT_TTL, result.model_dump_json())
    except Exception:
        logger.exception("VIN auction hit cache write failed")

    return result
