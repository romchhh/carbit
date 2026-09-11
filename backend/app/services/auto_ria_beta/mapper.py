from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.core.text import norm_text
from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.catalog import resolve_mark_id, resolve_model_id
from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.constants import REGION_TO_STATE_CITY
from app.services.auto_ria.mapper import sort_listings
from app.services.auto_ria_beta.constants import BASE_URL, CATEGORY_LEGKOVI, PAGE_SIZE
from app.services.auto_ria_beta.parser import VIN_RE, ScrapedCar, is_usa_import_text
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.listings.engine_volume import parse_engine_volume_from_text
from app.services.listings.plate import normalize_ua_plate
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


def _clean_vin(value: str | None) -> str | None:
    compact = re.sub(r"[^A-HJ-NPR-Z0-9]", "", (value or "").upper())
    return compact if VIN_RE.fullmatch(compact) else None


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, {}, [], "")}


def _vin_check_url(car_id: int) -> str:
    return f"{BASE_URL}/vin-check/auto/{car_id}/"


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

    details = dict(car.details or {})
    vin = _clean_vin(car.vin)
    plate = normalize_ua_plate(car.plate) or normalize_ua_plate(str(details.get("plate") or ""))
    raw_checked = details.get("vin_checked")
    if isinstance(raw_checked, bool):
        vin_checked = raw_checked
    elif details.get("vin_check") or vin:
        vin_checked = True
    else:
        vin_checked = None

    usa_import = details.get("usa_import")
    if usa_import is None and details.get("import_origin"):
        usa_import = is_usa_import_text(str(details.get("import_origin")))
    had_accident = details.get("had_accident")

    ria_page_badges: dict[str, bool] = {}
    if usa_import is True:
        ria_page_badges["usa_import"] = True
    elif usa_import is False:
        ria_page_badges["usa_import"] = False
    if had_accident is True:
        ria_page_badges["had_accident"] = True

    condition_flags: dict[str, bool] = {}
    if had_accident is True:
        condition_flags["had_accident"] = True
    elif had_accident is False:
        condition_flags["had_accident"] = False
        condition_flags["not_damaged"] = True
    if usa_import is True:
        condition_flags["usa_import"] = True

    fuel_name = car.fuel or ""
    engine_volume_l = parse_engine_volume_from_text(fuel_name) if fuel_name else None
    auto_data = _drop_empty(
        {
            "year": car.year,
            "fuelName": fuel_name or None,
            "gearboxName": car.transmission or None,
            "driveName": car.drive or None,
            "description": car.description,
            "raceInt": int(car.mileage_km / 1000) if car.mileage_km else None,
            "custom": 0 if details.get("not_customs") else None,
            "engineVolume": engine_volume_l,
            "generationName": details.get("generation_trim"),
        }
    )

    checked_vin = None
    if vin or vin_checked:
        checked_vin = _drop_empty(
            {
                "vin": vin,
                "isChecked": True if vin_checked else None,
                "isShow": True if vin else None,
                "linkToReport": _vin_check_url(car.car_id),
            }
        )

    display = details.get("display") if isinstance(details.get("display"), dict) else {}
    details_for_source = {key: value for key, value in details.items() if key != "photos"}

    source_data = _drop_empty(
        {
            "html_search": _drop_empty(
                {
                    "car_id": car.car_id,
                    "posted": car.posted,
                    "views": car.views,
                    "details": details_for_source,
                    "parser": "html",
                    "catalog": "new" if car.is_new else "used",
                }
            ),
            **display,
            "VIN": vin,
            "plateNumber": plate,
            "locationCityName": car.city,
            "USD": car.price_usd,
            "UAH": car.price_uah,
            "subCategoryName": car.body_type,
            "autoData": auto_data or None,
            "color": {"name": car.color} if car.color else None,
            "checkedVin": checked_vin,
            "ria_page_badges": ria_page_badges or None,
            "condition_flags": condition_flags or None,
            "autoInfoBar": {"damage": had_accident} if had_accident is not None else None,
            "technicalCondition": details.get("technical_condition"),
        }
    )

    seller_type = "dealer" if car.is_dealer else "private"
    listing_id = f"new_auto_ria_{car.car_id}" if car.is_new else f"auto_ria_{car.car_id}"
    return ListingOut(
        id=listing_id,
        source="auto_ria",
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
        seller_name=car.seller_name,
        vin=vin,
        plate=plate,
        vin_checked=True if vin_checked else None,
        vin_check_url=_vin_check_url(car.car_id) if vin or vin_checked else None,
        engine_volume_l=engine_volume_l,
        source_data=source_data,
        price_history=[],
        is_duplicate=False,
        is_new=True if car.is_new else None,
        published_at=_parse_posted(car.posted),
        found_at=now_kyiv(),
    )


async def filters_to_html_params(
    filters: SearchFilters,
    *,
    page: int,
    size: int = PAGE_SIZE,
    sort_by: str = "newest",
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "categories.main.id": CATEGORY_LEGKOVI,
        "page": max(page, 0),
        "size": min(max(size, 10), 100),
    }
    if sort_by in ("newest", "published_desc"):
        params["sort[0].order"] = "dates.created.desc"
    elif sort_by == "published_asc":
        params["sort[0].order"] = "dates.created.asc"

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
        if region_key not in REGION_TO_STATE_CITY:
            continue
        state_id, city_id = REGION_TO_STATE_CITY[region_key]
        # Сайт /uk/search/ ігнорує state[0].id / city[0].id (як у JSON API brand.id),
        # натомість фільтрує за state[0] / city[0] — ті самі ключі, що й у paid /auto/search.
        params["state[0]"] = state_id
        if city_id:
            params["city[0]"] = city_id
            break
        params.pop("city[0]", None)

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
    from app.services.listings.duplicates import mark_duplicates_in_pool

    return mark_duplicates_in_pool(sort_listings(listings, sort_by))
