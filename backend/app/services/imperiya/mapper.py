from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.text import norm_text
from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.imperiya.catalog import (
    resolve_make_id,
    resolve_model_id,
    resolve_region_ids_for_filters,
)
from app.services.imperiya.client import ImperiyaClient
from app.services.imperiya.constants import IMPERIYA_MAX_LIMIT, SORT_TO_IMPERIYA
from app.services.imperiya.errors import ImperiyaBrandNotFound
from app.services.search.subbrand_split import split_huawei_subbrand
from app.services.listings.seller_contact import apply_seller_contact_fields, seller_contact_from_imperiya
from app.services.listings.engine_volume import normalize_engine_litres, parse_engine_volume_from_text


def sort_to_imperiya(sort_by: str) -> str:
    return SORT_TO_IMPERIYA.get(sort_by, "date")


def _mileage_km(raw: Any) -> int:
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        return 0
    if value <= 0:
        return 0
    # API повертає пробіг у тисячах км (26 → 26 000).
    if value < 1000:
        return value * 1000
    return value


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return now_kyiv()
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return now_kyiv()


def _pick_price(ad: dict[str, Any], currency: str) -> tuple[int, str]:
    price = ad.get("price") if isinstance(ad.get("price"), dict) else {}
    cur = (currency or "USD").upper()
    if cur == "UAH":
        amount = int(price.get("uah") or 0)
        return amount, "UAH"
    if cur == "EUR":
        usd = int(price.get("usd") or 0)
        return usd, "USD"
    amount = int(price.get("usd") or 0)
    return amount, "USD"


def _extract_images(ad: dict[str, Any]) -> list[str]:
    images = ad.get("images") or []
    urls: list[str] = []
    for item in images:
        if not isinstance(item, dict):
            continue
        url = item.get("mediumUrl") or item.get("url") or item.get("smallUrl")
        if url and str(url).startswith("http"):
            urls.append(str(url))
    return urls


def ad_to_listing(ad: dict[str, Any], *, currency: str = "USD") -> ListingOut:
    ad_id = str(ad.get("id") or "")
    brand = str(ad.get("make") or "").strip()
    model = str(ad.get("model") or "").strip()
    title = str(ad.get("title") or "").strip() or " ".join(part for part in (brand, model) if part) or "Імперія Авто"
    city = str(ad.get("city") or "").strip()
    region_name = str(ad.get("region") or "").strip()
    region = ", ".join(part for part in (city, region_name) if part) or "Україна"

    price_amount, price_currency = _pick_price(ad, currency)
    engine_volume_l = parse_engine_volume_from_text(str(ad.get("engineVolume") or ""))
    if engine_volume_l is None:
        engine_volume_l = normalize_engine_litres(ad.get("engineVolume"))

    dealer = ad.get("dealer") if isinstance(ad.get("dealer"), dict) else None
    seller_type = "dealer" if dealer and dealer.get("name") else "private"

    return apply_seller_contact_fields(
        ListingOut(
        id=f"imperiya_{ad_id}",
        source="imperiya",
        title=title,
        brand=brand,
        model=model,
        year=int(ad.get("productionYear") or 0),
        price=price_amount,
        currency=price_currency,
        mileage=_mileage_km(ad.get("mileage")),
        fuel=str(ad.get("engineType") or "").strip(),
        transmission=str(ad.get("transmission") or "").strip(),
        region=region,
        description=(str(ad.get("description") or "").strip() or None),
        images=_extract_images(ad),
        url=str(ad.get("url") or "").strip(),
        seller_type=seller_type,
        vin=(str(ad.get("vin")).strip() if ad.get("vin") else None),
        engine_volume_l=engine_volume_l,
        source_data={"imperiya": ad},
        price_history=[],
        is_duplicate=False,
        published_at=_parse_datetime(ad.get("createdAt")),
        found_at=now_kyiv(),
        ),
        seller_contact_from_imperiya(ad),
    )


async def filters_to_search_params(
    client: ImperiyaClient,
    filters: SearchFilters,
    *,
    page: int,
    per_page: int,
    sort_by: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "page": max(page, 1),
        "limit": min(max(per_page, 1), IMPERIYA_MAX_LIMIT),
        "sortBy": sort_to_imperiya(sort_by),
    }

    brand = (filters.brand or "").strip()
    model = (filters.model or "").strip()
    brand, model = split_huawei_subbrand(brand, model)
    if brand:
        make_id = await resolve_make_id(client, brand)
        if make_id is None:
            raise ImperiyaBrandNotFound(f"Марку «{brand}» не знайдено в Імперія Авто")
        params["makeId"] = make_id
        if model:
            model_id = await resolve_model_id(client, make_id, model, brand=brand)
            if model_id is not None:
                params["modelId"] = model_id
            # Якщо modelId не знайдено — лишаємо пошук лише по makeId + пост-фільтр у Python.

    if filters.year_from:
        params["yearFrom"] = filters.year_from
    if filters.year_to:
        params["yearTo"] = filters.year_to

    if (filters.category or "").strip().lower() == "new":
        from app.services.search.category import new_category_year_bounds

        yf, yt = new_category_year_bounds(filters.year_from, filters.year_to)
        params["yearFrom"] = yf
        params["yearTo"] = yt

    filter_cur = resolve_filter_currency(filters.currency)
    if filters.price_from is not None:
        params["priceFrom"] = (
            filter_price_to_uah(filters.price_from, filter_cur)
            if filter_cur == "UAH"
            else filters.price_from
        )
    if filters.price_to is not None:
        params["priceTo"] = (
            filter_price_to_uah(filters.price_to, filter_cur)
            if filter_cur == "UAH"
            else filters.price_to
        )

    if filters.zero_mileage:
        params["mileageFrom"] = 0
        params["mileageTo"] = 0
    else:
        if filters.mileage_from is not None:
            params["mileageFrom"] = max(filters.mileage_from // 1000, 0)
        if filters.mileage_to is not None:
            params["mileageTo"] = max(filters.mileage_to // 1000, 0)

    if (filters.category or "").strip().lower() == "new":
        current_to = params.get("mileageTo")
        params["mileageFrom"] = params.get("mileageFrom", 0) or 0
        params["mileageTo"] = 1 if current_to is None else min(int(current_to), 1)

    regions: list[str] = []
    if filters.regions:
        regions.extend(str(r) for r in filters.regions if r)
    elif filters.region and norm_text(filters.region) not in ("вся україна", ""):
        regions.append(filters.region)

    region_ids = await resolve_region_ids_for_filters(client, regions)
    if region_ids:
        params["regionId"] = region_ids

    return params
