from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.core.text import norm_text
from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.car_market.constants import (
    BODY_CODES,
    BRAND_IDS,
    DRIVE_CODES,
    FUEL_CODES,
    TRANSMISSION_CODES,
)
from app.services.car_market.errors import CarMarketBrandNotFound
from app.services.car_market.parser import CarMarketCar
from app.services.listings.engine_volume import parse_engine_volume_from_text
from app.services.search.filter_multi import effective_brands
from app.services.search.subbrand_split import split_huawei_subbrand

_UA_MONTHS = {
    "січ": 1,
    "лют": 2,
    "бер": 3,
    "квіт": 4,
    "трав": 5,
    "черв": 6,
    "лип": 7,
    "серп": 8,
    "вер": 9,
    "жовт": 10,
    "лист": 11,
    "груд": 12,
}


def resolve_brand_id(brand: str) -> str | None:
    raw = brand.strip()
    if raw.isdigit():
        return raw
    key = norm_text(raw)
    if key in BRAND_IDS:
        return BRAND_IDS[key]
    for name, brand_id in BRAND_IDS.items():
        if key == norm_text(name) or key.startswith(norm_text(name)):
            return brand_id
    return None


def _first_code(values: list[str] | None, mapping: dict[str, str]) -> str | None:
    if not values:
        return None
    for value in values:
        code = mapping.get(norm_text(value))
        if code:
            return code
    return None


def filters_to_search_params(filters: SearchFilters, *, page: int) -> dict[str, Any]:
    params: dict[str, Any] = {"transport_type": "1"}

    brands = effective_brands(filters)
    if brands:
        brand = brands[0]
        brand, _model = split_huawei_subbrand(brand, (filters.model or "").strip())
        brand_id = resolve_brand_id(brand)
        if brand_id is None:
            raise CarMarketBrandNotFound(f"Марку «{brand}» не знайдено на Car Market")
        params["brands"] = brand_id

    if filters.price_from is not None:
        params["min_price"] = str(filters.price_from)
    if filters.price_to is not None:
        params["max_price"] = str(filters.price_to)
    if filters.year_from:
        params["year_from"] = str(filters.year_from)
    if filters.year_to:
        params["year_to"] = str(filters.year_to)

    fuel_code = _first_code(filters.fuel, FUEL_CODES)
    if fuel_code:
        params["fuels[]"] = fuel_code

    trans_code = _first_code(filters.transmission, TRANSMISSION_CODES)
    if trans_code:
        params["transmissions[]"] = trans_code

    drive_code = _first_code(filters.drivetrain, DRIVE_CODES)
    if drive_code:
        params["drives[]"] = drive_code

    if filters.body_types:
        for body in filters.body_types:
            code = BODY_CODES.get(norm_text(body))
            if code:
                params["body_types[]"] = code
                break

    if page > 1:
        params["page"] = str(page)

    return params


def _parse_date_added(text: str | None) -> datetime:
    if not text:
        return now_kyiv()
    m = re.search(r"(\d{1,2})\s+([а-яіїєґ]+)", text.strip().lower())
    if not m:
        return now_kyiv()
    day = int(m.group(1))
    month_key = m.group(2)[:4]
    month = _UA_MONTHS.get(month_key)
    if not month:
        return now_kyiv()
    now = now_kyiv()
    year = now.year
    if month > now.month + 1:
        year -= 1
    try:
        return datetime(year, month, day, 12, 0, tzinfo=KYIV_TZ)
    except ValueError:
        return now_kyiv()


def _split_brand_model(title: str, brand_hint: str | None = None) -> tuple[str, str]:
    title = title.strip()
    if not title:
        return "", ""
    if brand_hint:
        hint = brand_hint.strip()
        if title.lower().startswith(hint.lower()):
            model = title[len(hint) :].strip()
            return hint, model
    parts = title.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def car_to_listing(car: CarMarketCar, *, brand_hint: str | None = None) -> ListingOut:
    brand, model = _split_brand_model(car.title, brand_hint=brand_hint)
    listing_id = f"car_market_{car.car_id}" if car.car_id else f"car_market_{abs(hash(car.url))}"
    images = [car.image_url] if car.image_url else []
    engine_volume_l = parse_engine_volume_from_text(car.engine or "")

    return ListingOut(
        id=listing_id,
        source="car_market",
        title=car.title or "Car Market",
        brand=brand,
        model=model,
        year=int(car.year or 0),
        price=int(car.price_usd or 0),
        currency="USD",
        mileage=int(car.mileage_km or 0),
        fuel=(car.fuel or "").strip(),
        transmission=(car.transmission or "").strip(),
        region=(car.location or "Україна").strip(),
        description=car.listing_type,
        images=images,
        url=car.url,
        seller_type="dealer" if car.listing_type == "На майданчику" else "private",
        vin=None,
        engine_volume_l=engine_volume_l,
        source_data={
            "car_market": {
                "car_id": car.car_id,
                "listing_type": car.listing_type,
                "is_top": car.is_top,
                "is_sold": car.is_sold,
                "date_added": car.date_added,
            }
        },
        price_history=[],
        is_duplicate=False,
        published_at=_parse_date_added(car.date_added),
        found_at=now_kyiv(),
    )
