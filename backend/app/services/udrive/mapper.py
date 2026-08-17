from __future__ import annotations

from typing import Any

from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.listings.engine_volume import normalize_engine_litres
from app.services.listings.seller_contact import apply_seller_contact_fields
from app.services.search.subbrand_split import split_huawei_subbrand
from app.services.udrive.catalog import get_makes_by_id, resolve_make, resolve_model_ids
from app.services.udrive.client import UdriveClient
from app.services.udrive.constants import (
    FUEL_MAP,
    GEARBOX_MAP,
    STATUS_PUBLISHED,
    UDRIVE_CDN_BASE,
    UDRIVE_CDN_TRANSFORM,
    UDRIVE_PAGE_SIZE,
    UDRIVE_SITE_URL,
)
from app.services.udrive.errors import UdriveBrandNotFound


def blob_url(blob_id: str) -> str:
    return f"{UDRIVE_CDN_BASE}{blob_id}{UDRIVE_CDN_TRANSFORM}"


def extract_photos(car: dict[str, Any]) -> list[str]:
    photos: list[str] = []
    images = sorted(
        car.get("images") or [],
        key=lambda x: (x.get("sortIndex") is None, x.get("sortIndex") or 0),
    )
    for img in images:
        if not isinstance(img, dict):
            continue
        meta = img.get("metadata") if isinstance(img.get("metadata"), dict) else img
        bid = meta.get("blobId") if isinstance(meta, dict) else None
        if bid:
            url = blob_url(str(bid))
            if url not in photos:
                photos.append(url)
    return photos


def parse_price(price: Any) -> tuple[int | None, int | None]:
    """Повертає (uah, usd)."""
    if price is None:
        return None, None
    if isinstance(price, (int, float)):
        return int(price), None
    if not isinstance(price, dict):
        return None, None

    amount = price.get("amount")
    if isinstance(amount, dict):
        uah = amount.get("value")
        fx = amount.get("foreignCurrencyEquivalent") or {}
        usd = fx.get("amount") if isinstance(fx, dict) else None
        try:
            uah_i = int(uah) if uah is not None else None
        except (TypeError, ValueError):
            uah_i = None
        try:
            usd_i = int(usd) if usd is not None else None
        except (TypeError, ValueError):
            usd_i = None
        return uah_i, usd_i

    try:
        uah_i = int(price.get("amount")) if price.get("amount") is not None else None
    except (TypeError, ValueError):
        uah_i = None
    try:
        usd_i = int(price.get("foreignAmount")) if price.get("foreignAmount") is not None else None
    except (TypeError, ValueError):
        usd_i = None
    return uah_i, usd_i


def _pick_price(uah: int | None, usd: int | None, currency: str) -> tuple[int, str]:
    cur = (currency or "USD").upper()
    if cur == "UAH":
        if uah is not None:
            return uah, "UAH"
        if usd is not None:
            return usd, "USD"
        return 0, "UAH"
    if usd is not None:
        return usd, "USD"
    if uah is not None:
        return uah, "UAH"
    return 0, "USD"


def _map_fuel(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    return FUEL_MAP.get(key, str(raw or "").strip())


def _map_gearbox(raw: Any) -> str:
    key = str(raw or "").strip().lower()
    return GEARBOX_MAP.get(key, str(raw or "").strip())


def _mileage_km(car: dict[str, Any]) -> int:
    spec = car.get("specification") if isinstance(car.get("specification"), dict) else {}
    state = spec.get("state") if isinstance(spec.get("state"), dict) else {}
    raw = state.get("mileage")
    if raw is None:
        raw = car.get("mileage")
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        return 0
    return max(value, 0)


def car_to_listing(
    car: dict[str, Any],
    *,
    brand_slug: str,
    makes_by_id: dict[int, dict[str, Any]],
    currency: str = "USD",
) -> ListingOut:
    spec = car.get("specification") if isinstance(car.get("specification"), dict) else {}
    engine = spec.get("engine") if isinstance(spec.get("engine"), dict) else {}
    volume = engine.get("volume") if isinstance(engine.get("volume"), dict) else {}
    fuel = spec.get("fuel") if isinstance(spec.get("fuel"), dict) else {}
    drivetrain = spec.get("drivetrain") if isinstance(spec.get("drivetrain"), dict) else {}
    gearbox = drivetrain.get("gearbox") if isinstance(drivetrain.get("gearbox"), dict) else {}

    model_o = car.get("model") if isinstance(car.get("model"), dict) else {}
    trim_o = car.get("trim") if isinstance(car.get("trim"), dict) else {}
    dealer = (
        car.get("holderDealer")
        if isinstance(car.get("holderDealer"), dict)
        else (car.get("dealer") if isinstance(car.get("dealer"), dict) else {})
    )
    contact = dealer.get("salesContact") if isinstance(dealer.get("salesContact"), dict) else {}
    addr = contact.get("address") if isinstance(contact.get("address"), dict) else {}

    make_id = model_o.get("makeId")
    make_o = makes_by_id.get(int(make_id)) if make_id is not None else None
    make_o = make_o or {}

    brand = str(make_o.get("name") or "").strip()
    model = str(model_o.get("name") or "").strip()
    year = int(model_o.get("year") or 0)
    title_bits = [brand, model, str(trim_o.get("name") or "").strip(), str(year or "")]
    title = " ".join(x for x in title_bits if x).strip() or "uDrive"

    car_id = str(car.get("id") or "")
    slug = str(make_o.get("slug") or brand_slug or "car").strip() or "car"
    url = f"{UDRIVE_SITE_URL}/catalog/cars/{slug}/{car_id}" if car_id else UDRIVE_SITE_URL

    uah, usd = parse_price(car.get("price"))
    price_amount, price_currency = _pick_price(uah, usd, currency)

    city = str(addr.get("city") or "").strip()
    region = city or "Україна"

    engine_volume_l = normalize_engine_litres(volume.get("l"))
    if engine_volume_l is None and volume.get("cm3"):
        try:
            engine_volume_l = round(float(volume["cm3"]) / 1000, 1)
        except (TypeError, ValueError):
            engine_volume_l = None

    vin = spec.get("vin")
    seller_type = "dealer" if dealer.get("name") else "private"
    contact_payload = {
        "name": str(contact.get("name") or dealer.get("name") or "").strip() or None,
        "phone": str(contact.get("telephone") or "").strip() or None,
        "email": str(contact.get("email") or "").strip() or None,
    }

    listing = ListingOut(
        id=f"udrive_{car_id}",
        source="udrive",
        title=title,
        brand=brand,
        model=model,
        year=year,
        price=price_amount,
        currency=price_currency,
        mileage=_mileage_km(car),
        fuel=_map_fuel(fuel.get("type")),
        transmission=_map_gearbox(gearbox.get("type")),
        region=region,
        description=None,
        images=extract_photos(car),
        url=url,
        seller_type=seller_type,
        vin=(str(vin).strip() if vin else None),
        engine_volume_l=engine_volume_l,
        source_data={"udrive": car},
        price_history=[],
        is_duplicate=False,
        published_at=now_kyiv(),
        found_at=now_kyiv(),
    )
    return apply_seller_contact_fields(listing, contact_payload)


async def filters_to_query_body(
    client: UdriveClient,
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
) -> tuple[dict[str, Any], str]:
    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    brand, model = split_huawei_subbrand(brand, model)

    if not brand:
        raise UdriveBrandNotFound("Для пошуку в uDrive потрібна марка")

    make = await resolve_make(client, brand)
    if make is None or make.get("id") is None:
        raise UdriveBrandNotFound(f"Марку «{brand}» не знайдено в uDrive")

    make_id = int(make["id"])
    brand_slug = str(make.get("slug") or brand).strip().lower()
    model_ids: list[int] = []
    if model:
        from app.services.search.new_generation import new_generation_models

        names = new_generation_models(brand, model)
        seen: set[int] = set()
        for name in names or (model,):
            for mid in await resolve_model_ids(client, make_id, name, brand=brand):
                if mid not in seen:
                    seen.add(mid)
                    model_ids.append(mid)

    body: dict[str, Any] = {
        "makeId": [make_id],
        "fromPageNumber": max(page, 1),
        "toPageNumber": max(page, 1),
        "pageSize": min(max(per_page, 1), UDRIVE_PAGE_SIZE),
        "status": [STATUS_PUBLISHED],
    }
    if model_ids:
        body["modelId"] = model_ids

    from app.services.search.category import NEW_YEAR_MIN

    category = (filters.category or "all").strip().lower()
    year_from = filters.year_from
    if category == "new":
        year_from = max(int(year_from or 0), NEW_YEAR_MIN)

    if year_from or filters.year_to:
        year_filter: dict[str, int] = {}
        if year_from:
            year_filter["from"] = year_from
        if filters.year_to:
            year_filter["to"] = filters.year_to
        body["productionYear"] = year_filter

    filter_cur = resolve_filter_currency(filters.currency)
    if filters.price_from is not None or filters.price_to is not None:
        price_filter: dict[str, int] = {}
        if filters.price_from is not None:
            price_filter["from"] = (
                filters.price_from
                if filter_cur == "UAH"
                else filter_price_to_uah(filters.price_from, filter_cur)
            )
        if filters.price_to is not None:
            price_filter["to"] = (
                filters.price_to
                if filter_cur == "UAH"
                else filter_price_to_uah(filters.price_to, filter_cur)
            )
        body["price"] = price_filter

    return body, brand_slug
