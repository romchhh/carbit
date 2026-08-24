from __future__ import annotations

from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.listings.engine_volume import parse_engine_volume_from_text
from app.services.reono.parser import ReonoCar
from app.services.reono.region_paths import catalog_path_fallbacks, filters_to_catalog_path

__all__ = [
    "apply_client_filters",
    "car_to_listing",
    "catalog_path_fallbacks",
    "filters_to_catalog_path",
]


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
