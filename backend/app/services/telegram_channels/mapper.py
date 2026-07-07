from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.currency import infer_currency, to_uah
from app.core.config import settings
from app.core.timezone import as_kyiv, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters

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

def _norm(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def telegram_listing_id(channel: str, message_id: int) -> str:
    safe_channel = channel.strip("@").replace("/", "_").replace(" ", "_")
    return f"telegram_{safe_channel}_{message_id}"


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
    text = (listing.raw_text or "").strip().split("\n")[0]
    return text[:120] if text else "Telegram оголошення"


def car_listing_to_listing_out(listing: Any) -> ListingOut:
    raw_text = listing.raw_text or ""
    original_currency = infer_currency(
        float(listing.price_amount or 0),
        listing.price_currency,
        raw_text,
    )
    price_uah = to_uah(listing.price_amount, original_currency, text=raw_text)

    images = [telegram_media_url(path) for path in (listing.photos or [])[: settings.TELEGRAM_MAX_PHOTOS]]
    images = [url for url in images if url]

    posted_at = as_kyiv(listing.posted_at) if listing.posted_at else now_kyiv()

    return ListingOut(
        id=telegram_listing_id(listing.channel, listing.message_id),
        source="telegram",
        title=_build_title(listing),
        brand=listing.brand or "",
        model=listing.model or "",
        year=int(listing.year or 0),
        price=price_uah,
        currency="грн",
        mileage=int(listing.mileage_km or 0),
        fuel=FUEL_LABELS.get(listing.fuel_type or "", listing.fuel_type or ""),
        transmission=TRANSMISSION_LABELS.get(
            listing.transmission or "",
            listing.transmission or "",
        ),
        region=listing.location_city or "Україна",
        description=listing.raw_text,
        images=images,
        url=listing.source_link,
        seller_type="private",
        vin=None,
        vin_checked=None,
        vin_check_url=None,
        source_data={
            "channel": listing.channel,
            "message_id": listing.message_id,
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
    if filters.brand:
        brand = _norm(filters.brand)
        haystack = _norm(f"{item.brand} {item.title}")
        if brand not in haystack:
            item_brand = _norm(item.brand)
            if not item_brand or (brand not in item_brand and item_brand not in brand):
                return False

    if filters.model:
        model = _norm(filters.model)
        haystack = _norm(f"{item.model} {item.title}")
        if model not in haystack:
            return False

    if filters.year_from and item.year and item.year < filters.year_from:
        return False
    if filters.year_to and item.year and item.year > filters.year_to:
        return False

    if filters.price_from and item.price and item.price < filters.price_from:
        return False
    if filters.price_to and item.price and item.price > filters.price_to:
        return False

    if filters.mileage_from and item.mileage and item.mileage < filters.mileage_from:
        return False
    if filters.mileage_to and item.mileage and item.mileage > filters.mileage_to:
        return False

    if filters.region and _norm(filters.region) not in ("вся україна", ""):
        region = _norm(filters.region).removeprefix("м. ")
        item_region = _norm(item.region)
        generic_region = item_region in ("україна", "", "ukraine")
        if generic_region and item.source == "telegram":
            pass
        elif region not in item_region and item_region not in region:
            return False

    blob = _norm(f"{item.title} {item.fuel} {item.transmission} {item.description}")
    if filters.fuel and not any(_norm(value) in blob for value in filters.fuel):
        return False

    if filters.transmission and not any(
        _norm(value) in blob or _norm(value) in _norm(item.transmission) for value in filters.transmission
    ):
        return False

    return True
