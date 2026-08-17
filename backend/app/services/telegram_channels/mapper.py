from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.currency import infer_currency
from app.core.config import settings
from app.core.text import norm_text
from app.core.timezone import as_kyiv, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.listings.seller_contact import (
    apply_seller_contact_fields,
    seller_contact_from_telegram,
)
from app.services.search.brand_model_keywords import (
    text_matches_brand_filter,
    text_matches_model_filter,
    title_indicates_other_brand,
)
from app.services.telegram_channels.bootstrap import ensure_parser_path

ensure_parser_path()
from parser.channel_links import is_numeric_channel_id, public_telegram_message_url

TRANSMISSION_FILTER_ALIASES: dict[str, tuple[str, ...]] = {
    "автомат": (
        "автомат",
        "акпп",
        "automatic",
        "automat",
        "cvt",
        "варіатор",
        "variator",
        "robot",
        "робот",
        "dsg",
        "tiptronic",
        "типтронік",
        "typtronic",
    ),
    "механіка": ("механ", "manual", "мкпп", "mkpp", "мех"),
    "механика": ("механ", "manual", "мкпп", "mkpp", "мех"),
    "робот": ("robot", "dsg", "робот"),
    "варіатор": ("variator", "cvt", "варіатор"),
}


def _transmission_matches_filter(item: ListingOut, filter_values: list[str]) -> bool:
    blob = norm_text(f"{item.title} {item.fuel} {item.transmission} {item.description}")
    item_t = norm_text(item.transmission or "")
    for value in filter_values:
        key = norm_text(value)
        aliases = TRANSMISSION_FILTER_ALIASES.get(key, (key,))
        if any(alias in blob or alias in item_t for alias in aliases):
            return True
    return False

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


def telegram_text_is_sold_or_promo(text: str) -> bool:
    """Пост «ПРОДАНО» / реклама каналу — не показуємо в пошуку."""
    if not (text or "").strip():
        return False
    from app.services.telegram_channels.bootstrap import ensure_parser_path

    ensure_parser_path()
    from parser.extractor import is_sold_or_channel_promo

    return is_sold_or_channel_promo(text)


def telegram_text_is_non_listing(text: str) -> bool:
    """Запит на купівлю, sold-анонс або промо — не активне оголошення."""
    return telegram_text_is_search_request(text) or telegram_text_is_sold_or_promo(text)


def fix_telegram_listing_url(
    listing_id: str,
    url: str,
    *,
    images: list[str] | None = None,
) -> str:
    """Виправляє посилання t.me/… → канонічний t.me/username/msg з listing_id."""
    if listing_id.startswith("telegram_"):
        body = listing_id.removeprefix("telegram_")
        channel_part, _, msg_part = body.rpartition("_")
        if channel_part and msg_part.isdigit() and not is_numeric_channel_id(channel_part):
            return f"https://t.me/{channel_part}/{msg_part}"

    if not url or "t.me/-" not in url:
        return url

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


def _looks_like_dealer(text: str) -> bool:
    low = (text or "").lower()
    return any(
        token in low
        for token in (
            "автосалон",
            "автосалоні",
            "салон «",
            "салон \"",
            "dealer",
            "автодилер",
            "imperiya",
            "імперія авто",
        )
    )


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
        # Знімаємо emoji-префікси («🚗 Land Rover …»), а не пропускаємо рядок
        candidate = re.sub(
            r"^[\s📉📈🔴🟢🚗💰📍✍️👉✅☎️📞⚙️🛣🎨💺]+",
            "",
            candidate,
        ).strip()
        if len(candidate) < 4:
            continue
        low = candidate.lower()
        if low in {"facelift", "restyling", "нова", "продаж", "продаю", "продам", "ціну знижено"}:
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

    return apply_seller_contact_fields(
        ListingOut(
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
        seller_type="dealer" if _looks_like_dealer(raw_text) else "private",
        engine_volume_l=listing.engine_volume_l,
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
            "engine_volume_l": listing.engine_volume_l,
            "drive_type": listing.drive_type,
            "fuel_type": listing.fuel_type,
            "transmission": listing.transmission,
        },
        price_history=[],
        is_duplicate=False,
        published_at=posted_at,
        found_at=now_kyiv(),
        ),
        seller_contact_from_telegram(
            phone=listing.phone,
            contact_username=listing.contact_username,
            description=listing.raw_text,
        ),
    )


def _listing_matches_single_brand(
    item: ListingOut,
    haystack: str,
    brand: str,
    *,
    model_hint: str = "",
) -> bool:
    if not brand:
        return True

    # Ідентичність машини — заголовок + модель. Description НЕ входить:
    # там часто «краще за Audi / порівняння з Zeekr» → хибні матчі.
    identity = f"{item.title} {item.model or ''}".strip()
    if title_indicates_other_brand(identity, brand):
        return False

    item_brand_raw = (item.brand or "").strip()
    if item_brand_raw:
        from app.services.olx.brand_slugs import resolve_olx_brand_slug

        filter_slug = resolve_olx_brand_slug(brand)
        item_slug = resolve_olx_brand_slug(item_brand_raw)
        if filter_slug and item_slug and filter_slug == item_slug:
            # Структурований brand збігається, і заголовок не суперечить.
            return True

        if filter_slug and item_slug and filter_slug != item_slug:
            # Обидва бренди розпізнані і різні — довіряємо лише заголовку.
            from app.services.search.brand_model_keywords import (
                _allows_distinctive_model_without_brand,
                _brand_distinctive_model_in_text,
            )

            if text_matches_brand_filter(identity, brand):
                return True
            if _brand_distinctive_model_in_text(identity, brand):
                return True

            model_str = (model_hint or "").strip()
            if model_str and _allows_distinctive_model_without_brand(brand, model_str):
                if text_matches_model_filter(identity, model_str, brand=brand):
                    return True

            return False

    # brand порожній / не в каталозі — спочатку заголовок, потім повний текст.
    if text_matches_brand_filter(identity, brand, model=model_hint or ""):
        return True
    if not text_matches_brand_filter(haystack, brand, model=model_hint or ""):
        item_brand = norm_text(item.brand)
        brand_n = norm_text(brand)
        if not item_brand or (brand_n not in item_brand and item_brand not in brand_n):
            return False
    # Description згадав шукану марку, але заголовок уже перевірений на чужу марку вище.
    return True


def _listing_matches_model_name(
    item: ListingOut,
    model: str,
    *,
    brand: str = "",
) -> bool:
    if not model:
        return True

    # Заголовок — першоджерело; довгий дилерський опис не має ветошити збіг.
    title = item.title or ""
    if title and text_matches_model_filter(title, model, brand=brand or ""):
        return True

    text_haystack = f"{item.title} {item.description or ''}"
    if text_matches_model_filter(text_haystack, model, brand=brand or ""):
        return True

    item_model = (item.model or "").strip()
    if not item_model:
        return False
    if not text_matches_model_filter(item_model, model, brand=brand or ""):
        return False

    # Поле «model» могло бути проштамповане з фільтра (OLX/AUTO.RIA hint),
    # тож віримо йому лише коли заголовок не називає іншу модель цієї марки.
    from app.services.search.brand_model_keywords import text_names_other_model

    return not text_names_other_model(title or text_haystack, brand or item.brand or "", model)


def _listing_matches_single_model(
    item: ListingOut,
    model: str,
    *,
    brand: str = "",
    category: str = "",
) -> bool:
    if not model:
        return True

    names = [model]
    cat = (category or "").strip().lower()
    from app.services.search.category import listing_from_new_catalog
    from app.services.search.new_generation import new_generation_models

    if cat == "new" or listing_from_new_catalog(item):
        names = list(new_generation_models(brand, model)) or [model]

    return any(
        _listing_matches_model_name(item, name, brand=brand) for name in names
    )


def listing_out_matches_filters(item: ListingOut, filters: SearchFilters) -> bool:
    if item.source == "telegram" and telegram_text_is_non_listing(
        item.description or item.title or ""
    ):
        return False

    if (item.source or "").lower() == "telegram":
        from app.services.telegram_channels.freshness import telegram_listing_is_fresh

        if not telegram_listing_is_fresh(
            getattr(item, "published_at", None),
            found_at=getattr(item, "found_at", None),
        ):
            return False

    haystack = f"{item.brand} {item.title} {item.description or ''}"

    from app.services.search.filter_multi import effective_brands, effective_models, effective_regions

    brands = effective_brands(filters)
    models = effective_models(filters)

    if brands or models:
        brand_candidates = brands or [""]
        model_candidates = models or [""]
        matched = False
        for brand in brand_candidates:
            for model in model_candidates:
                if not _listing_matches_single_brand(
                    item, haystack, brand, model_hint=model
                ):
                    continue
                if not _listing_matches_single_model(
                    item, model, brand=brand, category=filters.category or ""
                ):
                    continue
                matched = True
                break
            if matched:
                break
        if not matched:
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

    regions = effective_regions(filters)
    if regions:
        from app.services.search.region_match import (
            is_generic_location,
            listing_region_matches_filter,
            text_mentions_any_region,
        )

        own_region = item.region or ""
        if not is_generic_location(own_region):
            ok = any(listing_region_matches_filter(own_region, r) for r in regions)
        elif (item.source or "").lower() == "telegram":
            # У пості міста в окремому полі немає — шукаємо його в тексті, а
            # якщо там теж немає, показуємо: краще так, ніж втратити оголошення.
            text = f"{item.title or ''} {item.description or ''}"
            ok = (
                any(listing_region_matches_filter(text, r) for r in regions)
                if text_mentions_any_region(text)
                else True
            )
        else:
            # OLX/AUTO.RIA завжди віддають місто, тож «Україна» — це не Київ.
            ok = not (item.region or "").strip()
        if not ok:
            return False

    blob = norm_text(f"{item.title} {item.fuel} {item.transmission} {item.description}")
    if filters.fuel and not any(norm_text(value) in blob for value in filters.fuel):
        return False

    if filters.transmission and not _transmission_matches_filter(item, filters.transmission):
        return False

    from app.services.search.category import listing_matches_category

    if not listing_matches_category(item, filters.category):
        return False

    from app.services.search.advanced_filters import listing_matches_advanced_filters

    if not listing_matches_advanced_filters(item, filters):
        return False

    return True
