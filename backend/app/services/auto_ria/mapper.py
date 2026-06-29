from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.catalog import resolve_mark_id, resolve_model_id
from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.constants import (
    AUTO_RIA_SITE_URL,
    CURRENCY_UAH,
    DEFAULT_CATEGORY_ID,
    FUEL_NAME_TO_ID,
    GEARBOX_NAME_TO_ID,
    REGION_TO_STATE_CITY,
)


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


async def filters_to_search_params(
    client: AutoRiaClient,
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "category_id": DEFAULT_CATEGORY_ID,
        "page": max(page - 1, 0),
        "countpage": min(max(per_page, 1), 50),
        "status_id": 0,
        "searchType": 4,
    }

    mark_id = await resolve_mark_id(client, filters.brand or "")
    if mark_id is None and filters.brand:
        raise ValueError(f"Марку «{filters.brand}» не знайдено в AUTO.RIA")

    if mark_id is not None:
        params["marka_id[0]"] = mark_id
        model_id = await resolve_model_id(client, mark_id, filters.model or "")
        if filters.model and model_id is None:
            raise ValueError(f"Модель «{filters.model}» не знайдено в AUTO.RIA")
        params["model_id[0]"] = model_id or 0

    if filters.year_from:
        params["s_yers[0]"] = filters.year_from
    if filters.year_to:
        params["po_yers[0]"] = filters.year_to

    if filters.price_from is not None:
        params["price_ot"] = filters.price_from
        params["currency"] = CURRENCY_UAH
    if filters.price_to is not None:
        params["price_do"] = filters.price_to
        params["currency"] = CURRENCY_UAH

    if filters.mileage_from is not None:
        params["raceFrom"] = max(filters.mileage_from // 1000, 0)
    if filters.mileage_to is not None:
        params["raceTo"] = max(filters.mileage_to // 1000, 0)

    if filters.region and _norm(filters.region) not in ("вся україна", ""):
        region_key = _norm(filters.region)
        if region_key in REGION_TO_STATE_CITY:
            state_id, city_id = REGION_TO_STATE_CITY[region_key]
            params["state[0]"] = state_id
            params["city[0]"] = city_id

    if filters.fuel:
        for index, fuel in enumerate(filters.fuel[:3]):
            fuel_id = FUEL_NAME_TO_ID.get(_norm(fuel))
            if fuel_id:
                params[f"type[{index}]"] = fuel_id

    if filters.transmission:
        for index, gear in enumerate(filters.transmission[:3]):
            gear_id = GEARBOX_NAME_TO_ID.get(_norm(gear))
            if gear_id:
                params[f"gearbox[{index}]"] = gear_id

    return params


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.now(UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return datetime.now(UTC)


def info_to_listing(info: dict[str, Any]) -> ListingOut:
    auto_data = info.get("autoData") or {}
    state_data = info.get("stateData") or {}
    photo_data = info.get("photoData") or {}

    auto_id = str(auto_data.get("autoId") or "")

    link = str(info.get("linkToView") or "")
    url = link if link.startswith("http") else f"{AUTO_RIA_SITE_URL}{link}"

    images: list[str] = []
    for key in ("seoLinkF", "seoLinkM", "seoLinkB"):
        if photo_data.get(key):
            images.append(str(photo_data[key]))
    if not images and isinstance(photo_data.get("all"), list) and photo_data["all"]:
        first = photo_data["all"][0]
        if isinstance(first, str) and first.startswith("http"):
            images.append(first)

    region_parts = [
        str(state_data.get("name") or info.get("locationCityName") or ""),
        str(state_data.get("regionName") or ""),
    ]
    region = ", ".join(part for part in region_parts if part) or "Україна"

    title = str(info.get("title") or "").strip()
    brand = str(info.get("markName") or "").strip()
    model = str(info.get("modelName") or "").strip()
    if not title:
        title = " ".join(part for part in (brand, model) if part) or "AUTO.RIA"

    price = int(info.get("UAH") or 0)
    year = int(auto_data.get("year") or 0)
    mileage = int(auto_data.get("raceInt") or 0) * 1000 if auto_data.get("raceInt") else 0

    fuel_raw = str(auto_data.get("fuelName") or "")
    fuel = fuel_raw.split(",")[0].strip() if fuel_raw else ""
    transmission = str(auto_data.get("gearboxName") or "")

    seller_type = "dealer" if info.get("dealer") else "private"

    return ListingOut(
        id=f"auto_ria_{auto_id}",
        source="auto_ria",
        title=title,
        brand=brand,
        model=model,
        year=year,
        price=price,
        currency="грн",
        mileage=mileage,
        fuel=fuel,
        transmission=transmission,
        region=region,
        description=str(info.get("infoBarText") or "") or None,
        images=images,
        url=url,
        seller_type=seller_type,
        price_history=[],
        is_duplicate=False,
        published_at=_parse_datetime(info.get("addDate")),
        found_at=datetime.now(UTC),
    )


def sort_listings(items: list[ListingOut], sort_by: str) -> list[ListingOut]:
    if sort_by == "price_desc":
        return sorted(items, key=lambda x: x.price, reverse=True)
    if sort_by == "year_desc":
        return sorted(items, key=lambda x: x.year, reverse=True)
    if sort_by == "mileage_asc":
        return sorted(items, key=lambda x: x.mileage)
    return sorted(items, key=lambda x: x.price)
