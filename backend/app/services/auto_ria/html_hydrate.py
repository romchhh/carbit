"""Гідратація AUTO.RIA через HTML сторінку оголошення (без платного API)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.schemas.schemas import ListingOut
from app.services.auto_ria.constants import AUTO_RIA_SITE_URL
from app.services.auto_ria.html_merge import merge_html_card_with_api
from app.services.auto_ria_beta.client import AutoRiaBetaClient
from app.services.auto_ria_beta.errors import AutoRiaBetaError
from app.services.auto_ria_beta.mapper import car_to_listing
from app.services.auto_ria_beta.parser import ScrapedCar

logger = logging.getLogger(__name__)

_HTML_ENRICH_SEM = asyncio.Semaphore(6)
_LISTING_ID_RE = re.compile(r"^(?:new_)?auto_ria(?:_beta)?_(\d+)$")


def auto_ria_listing_url(car_id: int | str, *, is_new: bool = False) -> str:
    """Короткий публічний URL (linkToView) — працює без slug марки/моделі."""
    cid = str(car_id).strip()
    if is_new:
        return f"{AUTO_RIA_SITE_URL}/newauto/{cid}.html"
    return f"{AUTO_RIA_SITE_URL}/auto/{cid}.html"


def parse_auto_ria_listing_id(listing_id: str | None) -> tuple[int | None, bool]:
    """Повертає (car_id, is_new)."""
    lid = (listing_id or "").strip()
    if lid.startswith("new_auto_ria_"):
        suffix = lid.removeprefix("new_auto_ria_")
        return (int(suffix), True) if suffix.isdigit() else (None, False)
    match = _LISTING_ID_RE.match(lid)
    if match:
        return int(match.group(1)), False
    return None, False


def listing_to_scraped_car(listing: ListingOut) -> ScrapedCar | None:
    car_id, is_new = parse_auto_ria_listing_id(listing.id)
    url = (listing.url or "").strip()
    if car_id is None or not url:
        return None

    sd: dict[str, Any] = listing.source_data if isinstance(listing.source_data, dict) else {}
    html_sd = sd.get("html_search") if isinstance(sd.get("html_search"), dict) else {}
    price_usd = sd.get("USD")
    price_uah = sd.get("UAH")

    return ScrapedCar(
        car_id=car_id,
        url=url,
        brand=listing.brand or None,
        model=listing.model or None,
        year=listing.year or None,
        price_usd=int(price_usd) if isinstance(price_usd, (int, float)) and price_usd else None,
        price_uah=int(price_uah) if isinstance(price_uah, (int, float)) and price_uah else None,
        mileage_km=listing.mileage or None,
        city=listing.region or None,
        fuel=listing.fuel or None,
        transmission=listing.transmission or None,
        vin=listing.vin,
        plate=listing.plate,
        photo_url=listing.images[0] if listing.images else None,
        photos=list(listing.images or []),
        is_new=is_new,
        posted=str(html_sd.get("posted") or "") or None,
        is_dealer=listing.seller_type == "dealer",
        seller_name=listing.seller_name,
        details=dict(html_sd.get("details") or {}) if isinstance(html_sd.get("details"), dict) else {},
    )


async def enrich_listing_from_html(
    *,
    url: str,
    car_id: int,
    is_new: bool = False,
    card: ListingOut | None = None,
) -> ListingOut | None:
    """Парсить сторінку оголошення; card — картка з пошуку для злиття бейджів/дат."""
    listing_url = (url or "").strip()
    if not listing_url:
        return card

    car = listing_to_scraped_car(card) if card is not None else None
    if car is None:
        car = ScrapedCar(car_id=car_id, url=listing_url, is_new=is_new)
    elif car.url != listing_url:
        car = ScrapedCar(
            car_id=car_id,
            url=listing_url,
            is_new=is_new,
            brand=car.brand,
            model=car.model,
            year=car.year,
            price_usd=car.price_usd,
            price_uah=car.price_uah,
            mileage_km=car.mileage_km,
            city=car.city,
            fuel=car.fuel,
            transmission=car.transmission,
            photo_url=car.photo_url,
            photos=list(car.photos or []),
            posted=car.posted,
            is_dealer=car.is_dealer,
            seller_name=car.seller_name,
            details=dict(car.details or {}),
        )

    try:
        async with _HTML_ENRICH_SEM:
            client = AutoRiaBetaClient()
            await client.enrich_car(car)
    except AutoRiaBetaError:
        logger.debug("AUTO.RIA HTML enrich failed car_id=%s", car_id, exc_info=True)
        return card
    except Exception:
        logger.exception("AUTO.RIA HTML enrich error car_id=%s", car_id)
        return card

    enriched = car_to_listing(
        car,
        brand_hint=(card.brand if card else None) or car.brand,
        model_hint=(card.model if card else None) or car.model,
    )
    if card is not None:
        return merge_html_card_with_api(card, enriched)
    return enriched


async def batch_enrich_auto_ria_html(
    ids: list[str],
    *,
    html_cards: dict[str, ListingOut] | None = None,
    cache_prefix: str,
    cache_ttl: int,
    is_new: bool = False,
) -> dict[str, ListingOut]:
    """Батч HTML-гідратація з Redis-кешем (той самий ключ, що й раніше для API)."""
    if not ids:
        return {}

    from app.core.redis import get_redis

    cards = html_cards or {}
    result: dict[str, ListingOut] = {}
    pending: list[tuple[str, str, ListingOut | None]] = []

    try:
        redis = await get_redis()
        keys = [f"{cache_prefix}{aid}" for aid in ids]
        raws = await redis.mget(*keys)
        for aid, raw in zip(ids, raws):
            if raw:
                try:
                    result[aid] = ListingOut.model_validate(json.loads(raw))
                    continue
                except Exception:
                    pass
            card = cards.get(aid)
            url = (card.url if card else None) or auto_ria_listing_url(aid, is_new=is_new)
            pending.append((aid, url.strip(), card))
    except Exception:
        logger.exception("AUTO.RIA HTML enrich cache read failed")
        for aid in ids:
            card = cards.get(aid)
            url = (card.url if card else None) or auto_ria_listing_url(aid, is_new=is_new)
            pending.append((aid, url.strip(), card))

    if not pending:
        return result

    async def fetch_one(aid: str, url: str, card: ListingOut | None) -> tuple[str, ListingOut | None]:
        listing = await enrich_listing_from_html(
            url=url,
            car_id=int(aid),
            is_new=is_new,
            card=card,
        )
        return aid, listing

    fetched = await asyncio.gather(*(fetch_one(aid, url, card) for aid, url, card in pending))

    try:
        redis = await get_redis()
        pipe = redis.pipeline(transaction=False)
        for aid, listing in fetched:
            if listing is not None:
                result[aid] = listing
                pipe.setex(f"{cache_prefix}{aid}", cache_ttl, listing.model_dump_json())
        await pipe.execute()
    except Exception:
        for aid, listing in fetched:
            if listing is not None:
                result[aid] = listing

    return result
