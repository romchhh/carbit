from __future__ import annotations

import re

from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.listings.engine_volume import parse_engine_volume_from_text
from app.services.lubeavto.constants import CATALOGS, DEFAULT_CATALOG
from app.services.lubeavto.parser import LubeAvtoCar
from app.services.search.filter_multi import effective_brands
from app.services.search.subbrand_split import split_huawei_subbrand


def _slugify_latin(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII)
    return re.sub(r"\s+", "-", text).strip("-")


def filters_to_catalog_path(filters: SearchFilters, *, catalog: str = DEFAULT_CATALOG) -> str:
    path = CATALOGS.get(catalog, CATALOGS[DEFAULT_CATALOG])
    brands = effective_brands(filters)
    if brands:
        brand, model = split_huawei_subbrand(brands[0], (filters.model or "").strip())
        brand_slug = _slugify_latin(brand)
        if brand_slug:
            path = f"{path}/{brand_slug}"
        model_text = (model or (filters.model or "").strip()).strip()
        if model_text:
            model_slug = _slugify_latin(model_text)
            if model_slug:
                path = f"{path}/{model_slug}"
    return path


def car_to_listing(car: LubeAvtoCar, *, brand_hint: str | None = None) -> ListingOut:
    brand = (car.brand or brand_hint or "").strip()
    model = (car.model or "").strip()
    if brand_hint and not model and car.title.lower().startswith(brand_hint.lower()):
        model = car.title[len(brand_hint) :].strip()
        model = re.sub(r"\b(19[5-9]\d|20[0-3]\d)\b", "", model).strip()

    listing_id = f"lubeavto_{car.car_id}" if car.car_id else f"lubeavto_{abs(hash(car.url))}"
    images = [car.image_url] if car.image_url else []
    engine_volume_l = parse_engine_volume_from_text(car.engine or "")

    catalog_label = {
        "instore": "В наявності",
        "instoreusers": "В дорозі",
        "auction": "Аукціон",
    }.get(car.catalog, car.catalog)

    return ListingOut(
        id=listing_id,
        source="lubeavto",
        title=car.title or "Любе Авто",
        brand=brand,
        model=model,
        year=int(car.year or 0),
        price=int(car.price_usd or 0),
        currency="USD",
        mileage=int(car.mileage_km or 0),
        fuel=(car.fuel or "").strip(),
        transmission=(car.transmission or "").strip(),
        region="Львів",
        description=catalog_label if not car.badge else f"{catalog_label} · {car.badge}",
        images=images,
        url=car.url,
        seller_type="dealer",
        vin=car.vin,
        engine_volume_l=engine_volume_l,
        source_data={
            "lubeavto": {
                "car_id": car.car_id,
                "catalog": car.catalog,
                "badge": car.badge,
                "drive": car.drive,
                "mileage_raw": car.mileage_raw,
            }
        },
        price_history=[],
        is_duplicate=False,
        published_at=now_kyiv(),
        found_at=now_kyiv(),
    )
