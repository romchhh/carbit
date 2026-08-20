from __future__ import annotations

import re

from app.core.text import norm_text
from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.listings.engine_volume import parse_engine_volume_from_text
from app.services.reono.constants import REGION_SLUGS, REONO_CATALOG_PATH
from app.services.reono.parser import ReonoCar
from app.services.search.filter_multi import effective_brands
from app.services.search.subbrand_split import split_huawei_subbrand


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def _resolve_region(region: str | None) -> str | None:
    if not region:
        return None
    raw = region.strip()
    if not raw:
        return None
    key = norm_text(raw.removeprefix("м.").removeprefix("М."))
    if key in REGION_SLUGS:
        return REGION_SLUGS[key]
    latin = _slugify(raw)
    return REGION_SLUGS.get(latin, latin)


def filters_to_catalog_path(filters: SearchFilters, *, page: int) -> str:
    segments = [REONO_CATALOG_PATH]

    region = _resolve_region(filters.region)
    if region:
        segments.append(region)

    brands = effective_brands(filters)
    if brands:
        brand, _model = split_huawei_subbrand(brands[0], (filters.model or "").strip())
        segments.append(_slugify(brand))
        model = (filters.model or "").strip()
        if model:
            segments.append(_slugify(model))

    path = "/".join(segments)
    if page > 1:
        path = f"{path}/page={page}"
    return path


def car_to_listing(car: ReonoCar) -> ListingOut:
    brand = (car.brand or "").strip()
    model = (car.model or "").strip()
    listing_id = f"reono_{car.car_id}" if car.car_id else f"reono_{abs(hash(car.url))}"
    images = [car.image_url] if car.image_url else []
    engine_volume_l = parse_engine_volume_from_text(car.engine or "")

    return ListingOut(
        id=listing_id,
        source="reono",
        title=car.title or "REONO",
        brand=brand,
        model=model,
        year=int(car.year or 0),
        price=int(car.price_usd or 0),
        currency="USD",
        mileage=int(car.mileage_km or 0),
        fuel=(car.fuel or "").strip(),
        transmission=(car.transmission or "").strip(),
        region=(car.location or "Україна").strip(),
        description="Преміум" if car.is_premium else None,
        images=images,
        url=car.url,
        seller_type="dealer" if car.is_premium else "private",
        vin=None,
        engine_volume_l=engine_volume_l,
        source_data={
            "reono": {
                "car_id": car.car_id,
                "price_uah": car.price_uah,
                "is_new": car.is_new,
                "is_premium": car.is_premium,
            }
        },
        price_history=[],
        is_duplicate=False,
        published_at=now_kyiv(),
        found_at=now_kyiv(),
    )


def apply_client_filters(cars: list[ReonoCar], filters: SearchFilters) -> list[ReonoCar]:
    out = cars
    if filters.price_from is not None:
        out = [car for car in out if car.price_usd is not None and car.price_usd >= filters.price_from]
    if filters.price_to is not None:
        out = [car for car in out if car.price_usd is not None and car.price_usd <= filters.price_to]
    if filters.year_from is not None:
        out = [car for car in out if car.year is not None and car.year >= filters.year_from]
    if filters.year_to is not None:
        out = [car for car in out if car.year is not None and car.year <= filters.year_to]
    if filters.mileage_from is not None:
        out = [car for car in out if car.mileage_km is not None and car.mileage_km >= filters.mileage_from]
    if filters.mileage_to is not None:
        out = [car for car in out if car.mileage_km is not None and car.mileage_km <= filters.mileage_to]
    return out
