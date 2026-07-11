from __future__ import annotations

import re
from app.core.timezone import now_kyiv
from typing import Any

from app.core.text import norm_text
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.mapper import sort_listings
from app.services.olx.constants import (
    CATEGORY_TO_CONDITION,
    COLOR_NAME_TO_TOKEN,
    DRIVETRAIN_NAME_TO_TOKEN,
    FUEL_NAME_TO_KEY,
    REGION_TO_CITY_QUERY,
    TRANSMISSION_NAME_TO_KEY,
)
from app.services.olx.dates import resolve_olx_published_at
from app.services.olx.parser import OlxListing, OlxSearchParams, is_valid_image_url
from app.services.olx.brand_slugs import resolve_olx_brand_slug, resolve_olx_model_slug
from app.services.olx.constants import MODEL_SLUG_ALIASES
from app.services.currency import filter_price_to_uah, resolve_filter_currency, to_uah


def brand_slug(brand: str) -> str:
    return resolve_olx_brand_slug(brand)


def model_slug(model: str, *, brand: str = "") -> str:
    key = norm_text(model)
    if key in MODEL_SLUG_ALIASES:
        return MODEL_SLUG_ALIASES[key]
    return resolve_olx_model_slug(model, brand=brand)


def filters_to_olx_params(filters: SearchFilters, *, max_pages: int = 2) -> OlxSearchParams:
    params = OlxSearchParams(max_pages=max_pages)

    if filters.brand:
        params.brand = brand_slug(filters.brand)
    if filters.model:
        params.model = model_slug(filters.model, brand=filters.brand or "")

    if filters.category and filters.category != "all":
        params.condition = CATEGORY_TO_CONDITION.get(filters.category)

    if filters.region and norm_text(filters.region) not in ("вся україна", ""):
        params.city_query = REGION_TO_CITY_QUERY.get(norm_text(filters.region), slugify_region(filters.region))

    params.price_from = filter_price_to_uah(filters.price_from, filters.currency)
    params.price_to = filter_price_to_uah(filters.price_to, filters.currency)
    params.currency = resolve_filter_currency(filters.currency)
    params.year_from = filters.year_from
    params.year_to = filters.year_to

    if filters.mileage_from is not None:
        params.mileage_from = max(filters.mileage_from // 1000, 0)
    if filters.mileage_to is not None:
        params.mileage_to = max(filters.mileage_to // 1000, 0)

    params.engine_from = filters.engine_volume_from
    params.engine_to = filters.engine_volume_to

    if filters.fuel:
        for fuel in filters.fuel:
            key = FUEL_NAME_TO_KEY.get(norm_text(fuel))
            if key:
                params.fuel = key
                break

    if filters.transmission:
        for gear in filters.transmission:
            key = TRANSMISSION_NAME_TO_KEY.get(norm_text(gear))
            if key:
                params.transmission = key
                break

    if filters.drivetrain:
        for drive in filters.drivetrain:
            token = DRIVETRAIN_NAME_TO_TOKEN.get(norm_text(drive))
            if token:
                params.drivetrain = token
                break

    if filters.colors:
        for color in filters.colors:
            token = COLOR_NAME_TO_TOKEN.get(norm_text(color), norm_text(color))
            params.color = token
            break

    params.consumption_from = filters.fuel_consumption_from
    params.consumption_to = filters.fuel_consumption_to
    params.ev_range_from = filters.ev_range_from
    params.ev_range_to = filters.ev_range_to
    params.battery_from = filters.battery_capacity_from
    params.battery_to = filters.battery_capacity_to
    params.power_from = filters.power_from
    params.power_to = filters.power_to

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


def _listing_price_value(listing: OlxListing) -> int:
    price = _parse_int(listing.price)
    if not price:
        return 0
    return to_uah(price, listing.currency)


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


def _split_brand_model(title: str, brand_hint: str = "", model_hint: str = "") -> tuple[str, str]:
    brand = brand_hint.strip()
    model = model_hint.strip()
    if brand and model:
        return brand, model
    if brand and title.lower().startswith(brand.lower()):
        remainder = title[len(brand) :].strip(" -·")
        return brand, model or remainder.split(",")[0].strip()
    parts = title.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1].split(",")[0].strip()
    return title, model


def olx_listing_to_listing_out(
    listing: OlxListing,
    *,
    brand_hint: str = "",
    model_hint: str = "",
) -> ListingOut:
    listing_id = listing.listing_id or "unknown"
    title = (listing.title or "OLX").strip()
    brand, model = _split_brand_model(title, brand_hint, model_hint)

    specs = listing.specs or {}
    fuel = _extract_spec(specs, "палив", "fuel") or ""
    transmission = _extract_spec(specs, "короб", "transmission", "кпп") or ""
    images = _listing_images(listing)

    price_uah = _listing_price_value(listing)

    return ListingOut(
        id=f"olx_{listing_id}",
        source="olx",
        title=title,
        brand=brand,
        model=model,
        year=_listing_year_value(listing),
        price=price_uah,
        currency="грн",
        mileage=_listing_mileage_value(listing),
        fuel=fuel,
        transmission=transmission,
        region=listing.city or "Україна",
        description=listing.description,
        images=images,
        url=listing.url or "",
        seller_type="private",
        vin=listing.vin,
        vin_checked=None,
        vin_check_url=None,
        source_data={
            "specs": specs,
            "published": listing.published,
            "promoted": listing.promoted,
            "raw_params": listing.raw_params,
            "price_original": _parse_int(listing.price),
            "price_currency": listing.currency or "UAH",
        },
        price_history=[],
        is_duplicate=False,
        published_at=resolve_olx_published_at(
            published=listing.published,
            raw_params=listing.raw_params,
        ),
        found_at=now_kyiv(),
    )


__all__ = ["filters_to_olx_params", "olx_listing_to_listing_out", "sort_listings"]
