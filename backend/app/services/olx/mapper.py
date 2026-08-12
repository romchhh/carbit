from __future__ import annotations

import re
from app.core.timezone import now_kyiv
from typing import Any

from app.core.text import norm_text
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.olx.constants import (
    BODY_NAME_TO_ENUM,
    CAR_FROM_USA,
    CATEGORY_TO_CONDITION,
    COLOR_NAME_TO_ENUM,
    COLOR_NAME_TO_TOKEN,
    CONDITION_ENUM_AFTER_ACCIDENT,
    CONDITION_ENUM_FIRST_OWNER,
    CONDITION_ENUM_NOT_BIT,
    DRIVETRAIN_NAME_TO_TOKEN,
    FUEL_NAME_TO_KEY,
    KYIV_REGION_KEYS,
    MODEL_SLUG_ALIASES,
    OLX_KYIV_CITY_ID,
    REGION_TO_CITY_QUERY,
    REGION_TO_OLX_REGION_ID,
    TRANSMISSION_NAME_TO_KEY,
)
from app.services.olx.dates import resolve_olx_published_at, resolve_olx_refreshed_at
from app.services.olx.parser import OlxListing, OlxSearchParams, is_valid_image_url
from app.services.olx.brand_slugs import (
    brand_model_forces_text_search,
    brand_uses_olx_text_search,
    compose_olx_text_query,
    resolve_olx_brand_slug,
    resolve_olx_model_slug,
)
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.search.subbrand_split import split_huawei_subbrand


def brand_slug(brand: str) -> str:
    return resolve_olx_brand_slug(brand)


def model_slug(model: str, *, brand: str = "") -> str:
    key = norm_text(model)
    if key in MODEL_SLUG_ALIASES:
        return MODEL_SLUG_ALIASES[key]
    return resolve_olx_model_slug(model, brand=brand)


def filters_to_olx_params(filters: SearchFilters, *, max_pages: int = 2) -> OlxSearchParams:
    params = OlxSearchParams(max_pages=max_pages)

    brand_raw = (filters.brand or "").strip()
    model_raw = (filters.model or "").strip()
    brand_raw, model_raw = split_huawei_subbrand(brand_raw, model_raw)

    if brand_raw:
        params.brand_label = brand_raw
    if model_raw:
        params.model_label = model_raw

    if brand_raw and (
        brand_uses_olx_text_search(brand_raw)
        or brand_model_forces_text_search(brand_raw, model_raw)
    ):
        # Немає taxonomy-path OLX (Zeekr / Tesla Model S / Toyota Prado тощо)
        # → /q-tesla-model-s/, /q-mersedes-gla/, /q-zeekr-001/ …
        params.text_query = compose_olx_text_query(brand_raw, model_raw) or brand_raw
    else:
        if brand_raw:
            params.brand = brand_slug(brand_raw)
        if model_raw:
            params.model = model_slug(model_raw, brand=brand_raw)

    if filters.category and filters.category != "all":
        params.condition = CATEGORY_TO_CONDITION.get(filters.category)

    if filters.region and norm_text(filters.region) not in ("вся україна", ""):
        params.region_label = filters.region.strip()
        region_key = norm_text(filters.region)
        if region_key in KYIV_REGION_KEYS:
            # API: city_id=268; HTML: /q-kyiv/ (search[city_id] на OLX не працює)
            params.city_id = OLX_KYIV_CITY_ID
            params.city_query = "kyiv"
        else:
            # HTML/API: search[region_id] / region_id (напр. Львівська=5)
            params.region_id = REGION_TO_OLX_REGION_ID.get(region_key)
            if params.region_id is None:
                # Луганська тощо без geo-id — fallback на /q-…/ + пост-фільтр
                params.city_query = REGION_TO_CITY_QUERY.get(
                    region_key, slugify_region(filters.region)
                )

    filter_cur = resolve_filter_currency(filters.currency)
    if filter_cur == "USD":
        params.price_from = filters.price_from
        params.price_to = filters.price_to
        params.currency = "USD"
    else:
        # UAH / EUR → суми в грн для URL і пост-фільтра
        params.price_from = filter_price_to_uah(filters.price_from, filter_cur)
        params.price_to = filter_price_to_uah(filters.price_to, filter_cur)
        params.currency = "UAH"
    params.year_from = filters.year_from
    params.year_to = filters.year_to

    if filters.zero_mileage:
        params.mileage_to = 0
    else:
        if filters.mileage_from is not None:
            params.mileage_from = max(filters.mileage_from // 1000, 0)
        if filters.mileage_to is not None:
            params.mileage_to = max(filters.mileage_to // 1000, 0)

    params.engine_from = filters.engine_volume_from
    params.engine_to = filters.engine_volume_to

    if filters.fuel:
        fuels: list[str] = []
        for fuel in filters.fuel:
            key = FUEL_NAME_TO_KEY.get(norm_text(fuel))
            if key and key not in fuels:
                fuels.append(key)
        params.fuels = fuels
        params.fuel = fuels[0] if fuels else None

    if filters.transmission:
        gears: list[str] = []
        for gear in filters.transmission:
            gear_key = norm_text(gear)
            key = "tiptronic" if "типтрон" in gear_key else TRANSMISSION_NAME_TO_KEY.get(gear_key)
            if key and key not in gears:
                gears.append(key)
        params.transmissions = gears
        params.transmission = gears[0] if gears else None

    if filters.drivetrain:
        drives: list[str] = []
        for drive in filters.drivetrain:
            token = DRIVETRAIN_NAME_TO_TOKEN.get(norm_text(drive))
            if token and token not in drives:
                drives.append(token)
        params.drivetrains = drives
        params.drivetrain = drives[0] if drives else None

    if filters.colors:
        color_enums: list[str] = []
        for color in filters.colors:
            color_key = norm_text(color)
            enum_id = COLOR_NAME_TO_ENUM.get(color_key)
            if enum_id and enum_id not in color_enums:
                color_enums.append(enum_id)
            if params.color is None:
                params.color = COLOR_NAME_TO_TOKEN.get(color_key, color_key)
                params.color_enum = enum_id
        params.color_enums = color_enums

    if filters.body_types:
        bodies: list[str] = []
        for body in filters.body_types:
            enum_id = BODY_NAME_TO_ENUM.get(norm_text(body))
            if enum_id and enum_id not in bodies:
                bodies.append(enum_id)
        params.body_enums = bodies

    if filters.usa_import and str(filters.usa_import).strip().lower() == "show":
        params.car_from_enums = [CAR_FROM_USA]

    condition_enums: list[str] = []
    if filters.accident == "none":
        condition_enums.append(CONDITION_ENUM_NOT_BIT)
    elif filters.accident == "had":
        condition_enums.append(CONDITION_ENUM_AFTER_ACCIDENT)
    if filters.owners_max == 1:
        condition_enums.append(CONDITION_ENUM_FIRST_OWNER)
    params.condition_enums = condition_enums

    params.consumption_from = filters.fuel_consumption_from
    params.consumption_to = filters.fuel_consumption_to
    params.ev_range_from = filters.ev_range_from
    params.ev_range_to = filters.ev_range_to
    params.battery_from = filters.battery_capacity_from
    params.battery_to = filters.battery_capacity_to
    params.power_from = filters.power_from
    params.power_to = filters.power_to
    params.seats_from = filters.seats_from
    params.seats_to = filters.seats_to

    params.fetch_details = params.needs_detail_fetch()
    return params


def slugify_region(region: str) -> str:
    text = region.strip().lower()
    text = text.removeprefix("м. ")
    text = text.replace(" ", "-")
    return text


def _parse_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else 0


def _parse_mileage_km(value: str | None) -> int:
    if not value:
        return 0
    match = re.search(r"([\d\s]+)\s*тис", value)
    if match:
        return int(re.sub(r"\s", "", match.group(1)) or "0") * 1000
    match = re.search(r"([\d\s]+)", value)
    if not match:
        return 0
    thousands = int(re.sub(r"\s", "", match.group(1)) or "0")
    return thousands * 1000 if "тис" in value.lower() else thousands


def _extract_spec(specs: dict[str, Any], *keys: str) -> str:
    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        if any(key.lower() in spec_key.lower() for key in keys):
            return spec_value.strip()
    return ""


def _listing_images(listing: OlxListing) -> list[str]:
    candidates: list[str] = []
    if listing.photo_url:
        candidates.append(listing.photo_url)
    candidates.extend(listing.photos or [])
    seen: set[str] = set()
    images: list[str] = []
    for url in candidates:
        if is_valid_image_url(url) and url not in seen:
            seen.add(url)
            images.append(url)
    return images


def _listing_year_value(listing: OlxListing) -> int:
    year = _parse_int(listing.year)
    if year:
        return year
    specs = listing.specs or {}
    year = _parse_int(_extract_spec(specs, "рік", "year"))
    if year:
        return year
    match = re.search(r"(19[5-9]\d|20[0-4]\d)", listing.title or "")
    return int(match.group(1)) if match else 0


def _listing_price_value(listing: OlxListing) -> tuple[int, str]:
    from app.services.currency import infer_currency, normalize_currency

    price = _parse_int(listing.price)
    if not price:
        return 0, "USD"
    currency = normalize_currency(listing.currency) if listing.currency else infer_currency(price, None)
    if currency not in {"UAH", "USD", "EUR"}:
        currency = infer_currency(price, None)
    return price, currency


def _listing_mileage_value(listing: OlxListing) -> int:
    mileage = _parse_mileage_km(listing.mileage)
    if mileage:
        return mileage
    specs = listing.specs or {}
    spec_value = _extract_spec(specs, "пробіг", "mileage")
    if spec_value:
        parsed = _parse_mileage_km(spec_value)
        if parsed:
            return parsed
        digits = re.sub(r"[^\d]", "", spec_value)
        if digits:
            value = int(digits)
            return value if value > 1000 else value * 1000
    return 0


def _listing_engine_volume_value(listing: OlxListing) -> float | None:
    from app.services.olx.engine_volume import extract_olx_listing_engine_volume

    return extract_olx_listing_engine_volume(listing)


def _clean_model_token(model: str, *, brand: str = "") -> str:
    """Перше слово моделі без року/бренду (для структурованого поля)."""
    m = norm_text(model or "")
    m = re.sub(r"\b(19|20)\d{2}\b", "", m)
    m = re.sub(r"[^a-z0-9а-яёіїєґ\s-]", " ", m)
    brand_key = norm_text(brand or "")
    tokens = [t for t in m.split() if t and (not brand_key or t != brand_key)]
    return tokens[0] if tokens else m.strip()


def _hint_conflicts_with_title(title: str, brand_hint: str) -> bool:
    """Text-query видача OLX шумить: не підставляти марку фільтра в чуже авто."""
    if not title or not brand_hint:
        return False
    from app.services.search.brand_model_keywords import text_names_other_brand

    return text_names_other_brand(title, brand_hint)


def _split_brand_model(title: str, brand_hint: str = "", model_hint: str = "") -> tuple[str, str]:
    brand = brand_hint.strip()
    model = model_hint.strip()
    if brand and model and not _hint_conflicts_with_title(title, brand):
        return brand, model

    title_work = re.sub(
        r"^(продам|продаю|продаж|sale|sell)\s+",
        "",
        (title or "").strip(),
        flags=re.IGNORECASE,
    ).strip() or (title or "").strip()

    if brand and title_work.lower().startswith(brand.lower()):
        remainder = title_work[len(brand) :].strip(" -·")
        return brand, model or remainder.split(",")[0].strip()
    parts = title_work.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1].split(",")[0].strip()
    return title_work or title, model


def _listing_region_display(listing: OlxListing) -> str:
    raw = listing.raw_params if isinstance(listing.raw_params, dict) else {}
    location = raw.get("location")
    if isinstance(location, dict):
        path = location.get("pathName") or location.get("path_name")
        if isinstance(path, str) and path.strip():
            return path.strip()
    if listing.city:
        return listing.city.strip()
    return "Україна"


def olx_listing_to_listing_out(
    listing: OlxListing,
    *,
    brand_hint: str = "",
    model_hint: str = "",
) -> ListingOut:
    listing_id = listing.listing_id or "unknown"
    title = (listing.title or "OLX").strip()
    brand, model = _split_brand_model(title, brand_hint, model_hint)
    model = _clean_model_token(model, brand=brand) or (model.split()[0] if model else model)

    specs = listing.specs or {}
    fuel = _extract_spec(specs, "палив", "fuel") or ""
    transmission = _extract_spec(specs, "короб", "transmission", "кпп") or ""
    images = _listing_images(listing)

    price_amount, price_currency = _listing_price_value(listing)

    from app.services.vin import extract_vin

    vin = listing.vin or extract_vin(
        title,
        listing.description,
        " ".join(str(v) for v in specs.values() if isinstance(v, str)),
    )

    published_at = resolve_olx_published_at(
        published=listing.published,
        raw_params=listing.raw_params,
    )
    refreshed_at = resolve_olx_refreshed_at(
        published=listing.published,
        raw_params=listing.raw_params,
        published_at=published_at,
    )

    engine_volume_l = _listing_engine_volume_value(listing)

    raw_params = listing.raw_params if isinstance(listing.raw_params, dict) else {}
    seller_type = "dealer" if raw_params.get("isBusiness") else "private"

    return ListingOut(
        id=f"olx_{listing_id}",
        source="olx",
        title=title,
        brand=brand,
        model=model,
        year=_listing_year_value(listing),
        price=price_amount,
        currency=price_currency,
        mileage=_listing_mileage_value(listing),
        fuel=fuel,
        transmission=transmission,
        region=_listing_region_display(listing),
        description=listing.description,
        images=images,
        url=listing.url or "",
        seller_type=seller_type,
        vin=vin,
        vin_checked=None,
        vin_check_url=None,
        engine_volume_l=engine_volume_l,
        source_data={
            "specs": specs,
            "published": listing.published,
            "promoted": listing.promoted,
            "raw_params": listing.raw_params,
            "price_original": price_amount,
            "price_currency": price_currency,
            "engine_volume_l": engine_volume_l,
            "createdTime": (listing.raw_params or {}).get("createdTime")
            if isinstance(listing.raw_params, dict)
            else None,
            "lastRefreshTime": (listing.raw_params or {}).get("lastRefreshTime")
            if isinstance(listing.raw_params, dict)
            else None,
        },
        price_history=[],
        is_duplicate=False,
        published_at=published_at,
        refreshed_at=refreshed_at,
        found_at=now_kyiv(),
    )


__all__ = ["filters_to_olx_params", "olx_listing_to_listing_out"]
