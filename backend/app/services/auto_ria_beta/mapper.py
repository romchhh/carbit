from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.text import norm_text
from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.catalog import resolve_mark_id, resolve_model_id
from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.constants import REGION_TO_STATE_CITY
from app.services.auto_ria.mapper import sort_listings
from app.services.auto_ria_beta.constants import AUTO_RIA_BETA_SOURCE, CATEGORY_LEGKOVI, PAGE_SIZE
from app.services.auto_ria_beta.parser import ScrapedCar
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.search.filter_multi import effective_brands, effective_models, effective_regions
from app.services.telegram_channels.mapper import listing_out_matches_filters

AUTO_RIA_BETA_UNKNOWN_PUBLISHED_AT = datetime(1970, 1, 1, 12, 0, tzinfo=KYIV_TZ)


def _parse_posted(value: str | None) -> datetime:
    text = (value or "").strip()
    if not text:
        return AUTO_RIA_BETA_UNKNOWN_PUBLISHED_AT
    for fmt in ("%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=KYIV_TZ)
        except ValueError:
            continue
    return AUTO_RIA_BETA_UNKNOWN_PUBLISHED_AT


def _title_bits(car: ScrapedCar, brand_hint: str | None, model_hint: str | None) -> tuple[str, str, str]:
    brand = (brand_hint or car.brand or "").strip()
    if brand and not brand[0].isupper():
        brand = brand.title()
    model = (model_hint or car.model or "").strip()
    if model and model == model.upper():
        model = model.title()
    title = " ".join(part for part in (brand, model, str(car.year or "")) if part).strip()
    return brand, model, title or f"AUTO.RIA {car.car_id}"


def car_to_listing(
    car: ScrapedCar,
    *,
    brand_hint: str | None = None,
    model_hint: str | None = None,
    currency: str = "USD",
) -> ListingOut:
    brand, model, title = _title_bits(car, brand_hint, model_hint)
    use_usd = (currency or "USD").upper() == "USD" and car.price_usd is not None
    price = int(car.price_usd or car.price_uah or 0)
    listing_currency = "USD" if use_usd else "UAH"
    if not use_usd and car.price_uah is None and car.price_usd is not None:
        price = int(car.price_usd)
        listing_currency = "USD"

    images = list(car.photos or [])
    if not images and car.photo_url:
        images = [car.photo_url]

    seller_type = "dealer" if car.is_dealer else "private"
    source_data = {
        "auto_ria_beta": {
            "car_id": car.car_id,
            "posted": car.posted,
            "views": car.views,
            "details": car.details or {},
            "parser": "html",
        }
    }

    return ListingOut(
        id=f"auto_ria_beta_{car.car_id}",
        source=AUTO_RIA_BETA_SOURCE,
        title=title,
        brand=brand,
        model=model,
        year=int(car.year or 0),
        price=price,
        currency=listing_currency,
        mileage=int(car.mileage_km or 0),
        fuel=car.fuel or "",
        transmission=car.transmission or "",
        region=car.city or "",
        description=car.description,
        images=images,
        url=car.url,
        seller_type=seller_type,
        vin=car.vin if car.vin and len(car.vin) == 17 else None,
        source_data=source_data,
        price_history=[],
        is_duplicate=False,
        published_at=_parse_posted(car.posted),
        found_at=now_kyiv(),
    )


async def filters_to_html_params(
    filters: SearchFilters,
    *,
    page: int,
    size: int = PAGE_SIZE,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "categories.main.id": CATEGORY_LEGKOVI,
        "page": max(page, 0),
        "size": min(max(size, 10), 100),
    }

    brand = (effective_brands(filters)[:1] or [""])[0]
    model = (effective_models(filters)[:1] or [""])[0]
    client = AutoRiaClient()

    mark_id = await resolve_mark_id(client, brand) if brand else None
    if mark_id is not None:
        params["brand.id[0]"] = mark_id
        model_id = await resolve_model_id(client, mark_id, model) if model else None
        if model_id:
            params["model.id[0]"] = model_id

    if filters.year_from:
        params["year[0].gte"] = filters.year_from
    if filters.year_to:
        params["year[0].lte"] = filters.year_to

    if filters.price_from is not None or filters.price_to is not None:
        filter_cur = resolve_filter_currency(filters.currency)
        if filter_cur == "USD":
            if filters.price_from is not None:
                params["price.USD.gte"] = filters.price_from
            if filters.price_to is not None:
                params["price.USD.lte"] = filters.price_to
        else:
            if filters.price_from is not None:
                params["price.UAH.gte"] = filter_price_to_uah(filters.price_from, filter_cur)
            if filters.price_to is not None:
                params["price.UAH.lte"] = filter_price_to_uah(filters.price_to, filter_cur)

    for region in effective_regions(filters):
        region_key = norm_text(region)
        if region_key in REGION_TO_STATE_CITY:
            state_id, city_id = REGION_TO_STATE_CITY[region_key]
            params["state[0].id"] = state_id
            if city_id:
                params["city[0].id"] = city_id
            break

    category = (filters.category or "all").strip().lower()
    if filters.not_customs:
        customs = filters.not_customs.strip().lower()
        if customs == "show":
            params["custom"] = 1
        elif customs == "hide" and category != "import":
            params["custom"] = 0

    if category == "used":
        params["searchType"] = 4
        params["custom"] = 0
    elif category == "new":
        from app.services.search.category import new_category_year_bounds

        params["searchType"] = 1
        params["raceFrom"] = 0
        existing_to = params.get("raceTo")
        params["raceTo"] = 1 if existing_to is None else min(int(existing_to), 1)
        yf, yt = new_category_year_bounds(filters.year_from, filters.year_to)
        params["year[0].gte"] = yf
        params["year[0].lte"] = yt
    elif category == "import":
        params["searchType"] = 4
        params["custom"] = 1

    if filters.mileage_from is not None:
        params["raceFrom"] = max(int(filters.mileage_from / 1000), 0)
    if filters.mileage_to is not None:
        params["raceTo"] = max(int(filters.mileage_to / 1000), 0)

    return params


def apply_client_filters(cars: list[ScrapedCar], filters: SearchFilters) -> list[ScrapedCar]:
    out: list[ScrapedCar] = []
    for car in cars:
        listing = car_to_listing(car, brand_hint=(effective_brands(filters)[:1] or [None])[0])
        if listing_out_matches_filters(listing, filters):
            out.append(car)
    return out


def listings_from_cars(
    cars: list[ScrapedCar],
    filters: SearchFilters,
    *,
    sort_by: str,
) -> list[ListingOut]:
    brand_hint = (effective_brands(filters)[:1] or [None])[0]
    model_hint = (effective_models(filters)[:1] or [None])[0]
    currency = (filters.currency or "USD").upper()
    listings = [
        car_to_listing(car, brand_hint=brand_hint, model_hint=model_hint, currency=currency)
        for car in cars
    ]
    listings = [item for item in listings if listing_out_matches_filters(item, filters)]
    return sort_listings(listings, sort_by)
