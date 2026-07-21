from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.currency import infer_currency
from app.core.config import settings
from app.core.text import norm_text
from app.core.timezone import as_kyiv, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.brand_model_keywords import (
    text_matches_brand_filter,
    text_matches_model_filter,
)
from app.services.telegram_channels.bootstrap import ensure_parser_path

ensure_parser_path()
from parser.channel_links import is_numeric_channel_id, public_telegram_message_url

FUEL_LABELS = {
    "petrol": "Бензин",
    "diesel": "Дизель",
    "gas": "Газ",
    "gas_petrol": "Газ-бензин",
    "hybrid": "Гібрид",
    "electric": "Електро",
}

TRANSMISSION_LABELS = {
    "manual": "Механіка",
    "automatic": "Автомат",
    "robot": "Робот",
    "variator": "Варіатор",
}


def telegram_listing_id(channel: str, message_id: int) -> str:
    safe_channel = channel.strip("@").replace("/", "_").replace(" ", "_")
    return f"telegram_{safe_channel}_{message_id}"


def telegram_message_url(channel: str, message_id: int, current_url: str = "") -> str:
    slug = (channel or "").strip().lstrip("@")
    if slug and not is_numeric_channel_id(slug):
        return public_telegram_message_url(slug, message_id)
    return current_url or ""


def _channel_slug_from_telegram_images(images: list[str] | None) -> str:
    for image in images or []:
        marker = "/telegram-media/"
        if marker not in image:
            continue
        rel = image.split(marker, 1)[-1].strip("/")
        parts = rel.split("/")
        if len(parts) >= 2 and not is_numeric_channel_id(parts[0]):
            return parts[0]
    return ""


def telegram_text_is_search_request(text: str) -> bool:
    """Пост «шукаю авто», а не пропозиція продажу — не показуємо в пошуку."""
    if not (text or "").strip():
        return False
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.extractor import is_car_search_request

    return is_car_search_request(text)


def fix_telegram_listing_url(
    listing_id: str,
    url: str,
    *,
    images: list[str] | None = None,
) -> str:
    """Виправляє старі посилання t.me/-100... → t.me/username/msg."""
    if not url or "t.me/-" not in url:
        return url
    if listing_id.startswith("telegram_"):
        body = listing_id.removeprefix("telegram_")
        channel_part, _, msg_part = body.rpartition("_")
        if channel_part and msg_part.isdigit() and not is_numeric_channel_id(channel_part):
            return f"https://t.me/{channel_part}/{msg_part}"

    channel_slug = _channel_slug_from_telegram_images(images)
    if channel_slug:
        match = re.search(r"/(\d+)$", url)
        if match:
            return f"https://t.me/{channel_slug}/{match.group(1)}"
    return url


def telegram_media_url(local_path: str) -> str:
    media_root = Path(settings.TELEGRAM_MEDIA_DIR).resolve()
    path = Path(local_path).resolve()
    try:
        rel = path.relative_to(media_root)
    except ValueError:
        return ""
    return f"/api/v1/telegram-media/{rel.as_posix()}"


def _build_title(listing: Any) -> str:
    parts = [listing.brand, listing.model]
    title = " ".join(part for part in parts if part)
    if title:
        if listing.year:
            return f"{title} {listing.year}"
        return title
    text = (listing.raw_text or "").strip()
    for line in text.split("\n"):
        candidate = line.strip()
        if len(candidate) < 4:
            continue
        # Пропускаємо службові рядки / одну «хвостову» фічу типу Facelift
        low = candidate.lower()
        if low in {"facelift", "restyling", "нова", "продаж", "продаю", "продам"}:
            continue
        if candidate.startswith(("💰", "📍", "✍️", "👉", "🚗")):
            continue
        return candidate[:120]
    return "Telegram оголошення"


def car_listing_to_listing_out(listing: Any) -> ListingOut:
    raw_text = listing.raw_text or ""
    original_currency = infer_currency(
        float(listing.price_amount or 0),
        listing.price_currency,
        raw_text,
    )
    price_amount = int(round(float(listing.price_amount or 0)))

    images = [telegram_media_url(path) for path in (listing.photos or [])[: settings.TELEGRAM_MAX_PHOTOS]]
    images = [url for url in images if url]

    posted_at = as_kyiv(listing.posted_at) if listing.posted_at else now_kyiv()

    from app.services.vin import extract_vin

    flags = listing.condition_flags if isinstance(listing.condition_flags, dict) else {}
    vin = flags.get("vin") if isinstance(flags.get("vin"), str) else None
    if not vin:
        vin = extract_vin(raw_text, listing.brand, listing.model)

    message_ids = list(listing.group_message_ids or []) or [listing.message_id]
    photos_pending = not bool(images)

    return ListingOut(
        id=telegram_listing_id(listing.channel, listing.message_id),
        source="telegram",
        title=_build_title(listing),
        brand=listing.brand or "",
        model=listing.model or "",
        year=int(listing.year or 0),
        price=price_amount,
        currency=original_currency,
        mileage=int(listing.mileage_km or 0),
        fuel=FUEL_LABELS.get(listing.fuel_type or "", listing.fuel_type or ""),
        transmission=TRANSMISSION_LABELS.get(
            listing.transmission or "",
            listing.transmission or "",
        ),
        region=listing.location_city or "Україна",
        description=listing.raw_text,
        images=images,
        url=telegram_message_url(listing.channel, listing.message_id, listing.source_link),
        seller_type="private",
        vin=vin,
        vin_checked=None,
        vin_check_url=None,
        source_data={
            "channel": listing.channel,
            "message_id": listing.message_id,
            "photo_message_ids": message_ids,
            "photos_pending": photos_pending,
            "confidence": listing.confidence,
            "needs_review": listing.needs_review,
            "condition_flags": listing.condition_flags,
            "contact_username": listing.contact_username,
            "phone": listing.phone,
            "price_amount": listing.price_amount,
            "price_currency": original_currency,
            "price_original": listing.price_amount,
        },
        price_history=[],
        is_duplicate=False,
        published_at=posted_at,
        found_at=now_kyiv(),
    )


def listing_out_matches_filters(item: ListingOut, filters: SearchFilters) -> bool:
    if item.source == "telegram" and telegram_text_is_search_request(
        item.description or item.title or ""
    ):
        return False

    haystack = f"{item.brand} {item.title} {item.description or ''}"

    if filters.brand:
        # Жорстка відмова: структурована марка оголошення ≠ фільтр (якщо заголовок не підтверджує марку).
        item_brand_raw = (item.brand or "").strip()
        if item_brand_raw:
            from app.services.olx.brand_slugs import resolve_olx_brand_slug

            filter_slug = resolve_olx_brand_slug(filters.brand)
            item_slug = resolve_olx_brand_slug(item_brand_raw)
            title_matches_brand = text_matches_brand_filter(
                haystack, filters.brand, model=filters.model or ""
            )
            if (
                filter_slug
                and item_slug
                and filter_slug != item_slug
                and not title_matches_brand
            ):
                item_brand = norm_text(item.brand)
                brand = norm_text(filters.brand)
                if not item_brand or (brand not in item_brand and item_brand not in brand):
                    return False

        if not text_matches_brand_filter(
            haystack, filters.brand, model=filters.model or ""
        ):
            item_brand = norm_text(item.brand)
            brand = norm_text(filters.brand)
            if not item_brand or (brand not in item_brand and item_brand not in brand):
                return False

    if filters.model:
        model_haystack = f"{item.model} {item.title} {item.description or ''}"
        if not text_matches_model_filter(
            model_haystack,
            filters.model,
            brand=filters.brand or "",
        ):
            return False

    if filters.year_from or filters.year_to:
        # year=0 = невідомий рік → не проходить, коли користувач задав діапазон
        if not item.year:
            return False
        if filters.year_from and item.year < filters.year_from:
            return False
        if filters.year_to and item.year > filters.year_to:
            return False

    if filters.price_from or filters.price_to:
        from app.services.currency import filter_price_to_uah, listing_price_uah

        price_from = filter_price_to_uah(filters.price_from, filters.currency)
        price_to = filter_price_to_uah(filters.price_to, filters.currency)
        item_uah = listing_price_uah(item.price, item.currency)
        if price_from and item_uah and item_uah < price_from:
            return False
        if price_to and item_uah and item_uah > price_to:
            return False

    if filters.mileage_from and item.mileage and item.mileage < filters.mileage_from:
        return False
    if filters.mileage_to and item.mileage and item.mileage > filters.mileage_to:
        return False

    if filters.region and norm_text(filters.region) not in ("вся україна", ""):
        from app.services.search.region_match import listing_region_matches_filter

        # Telegram: місто часто лише в тексті поста («🌏Місто: Вінниця»),
        # а поле region може бути порожнім / «Україна».
        region_haystack = item.region or ""
        if (item.source or "").lower() == "telegram":
            region_haystack = f"{region_haystack} {item.title or ''} {item.description or ''}"
        if not listing_region_matches_filter(region_haystack, filters.region):
            return False

    blob = norm_text(f"{item.title} {item.fuel} {item.transmission} {item.description}")
    if filters.fuel and not any(norm_text(value) in blob for value in filters.fuel):
        return False

    if filters.transmission and not any(
        norm_text(value) in blob or norm_text(value) in norm_text(item.transmission) for value in filters.transmission
    ):
        return False

    from app.services.search.category import listing_matches_category

    if not listing_matches_category(item, filters.category):
        return False

    return True
