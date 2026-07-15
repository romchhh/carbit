from __future__ import annotations

from datetime import UTC, datetime

from app.core.timezone import KYIV_TZ, as_kyiv, now_kyiv
from typing import Any

from app.core.text import norm_text
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.catalog import resolve_mark_id, resolve_model_id
from app.services.auto_ria.client import AutoRiaClient
from app.services.auto_ria.details import extract_image_urls, sanitize_source_data
from app.services.auto_ria.constants import (
    AUTO_RIA_SITE_URL,
    CURRENCY_UAH,
    CURRENCY_USD,
    DEFAULT_CATEGORY_ID,
    FUEL_NAME_TO_ID,
    GEARBOX_NAME_TO_ID,
    REGION_TO_STATE_CITY,
)
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.notifications.freshness import auto_ria_top_for_max_hours


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

    if filters.price_from is not None or filters.price_to is not None:
        # AUTO.RIA: currency=1 → USD, currency=3 → UAH.
        # EUR у фільтрі конвертуємо в грн (API не має окремого EUR).
        filter_cur = resolve_filter_currency(filters.currency)
        if filter_cur == "USD":
            params["currency"] = CURRENCY_USD
            if filters.price_from is not None:
                params["price_ot"] = filters.price_from
            if filters.price_to is not None:
                params["price_do"] = filters.price_to
        else:
            params["currency"] = CURRENCY_UAH
            if filters.price_from is not None:
                params["price_ot"] = filter_price_to_uah(filters.price_from, filter_cur)
            if filters.price_to is not None:
                params["price_do"] = filter_price_to_uah(filters.price_to, filter_cur)

    if filters.mileage_from is not None:
        params["raceFrom"] = max(filters.mileage_from // 1000, 0)
    if filters.mileage_to is not None:
        params["raceTo"] = max(filters.mileage_to // 1000, 0)

    # Свіжі оголошення: top=1 (година), 8 (3г), 14 (12г), 11 (доба)…
    if filters.published_within_hours:
        top = auto_ria_top_for_max_hours(filters.published_within_hours)
        if top is not None:
            params["top"] = top
    elif filters.published_within_days:
        days = filters.published_within_days
        if days <= 1:
            params["top"] = 11
        elif days <= 2:
            params["top"] = 10
        elif days <= 3:
            params["top"] = 3
        else:
            params["top"] = 4

    if filters.region and norm_text(filters.region) not in ("вся україна", ""):
        region_key = norm_text(filters.region)
        if region_key in REGION_TO_STATE_CITY:
            state_id, city_id = REGION_TO_STATE_CITY[region_key]
            params["state[0]"] = state_id
            params["city[0]"] = city_id

    if filters.fuel:
        for index, fuel in enumerate(filters.fuel[:3]):
            fuel_id = FUEL_NAME_TO_ID.get(norm_text(fuel))
            if fuel_id:
                params[f"type[{index}]"] = fuel_id

    if filters.transmission:
        for index, gear in enumerate(filters.transmission[:3]):
            gear_id = GEARBOX_NAME_TO_ID.get(norm_text(gear))
            if gear_id:
                params[f"gearbox[{index}]"] = gear_id

    # Всі / Вживані / Нові / Під пригон
    category = (filters.category or "all").strip().lower()
    if category == "used":
        # Класичний вживаний парк (searchType=4), розмитнені.
        params["searchType"] = 4
        params["custom"] = 0
    elif category == "new":
        # «Нові / майже нові»: до 15 тис. км (race* — тисячі км).
        # ≤1 тис. занадто вузько для свіжих EV (Zeekr 5–12 тис. км).
        params["searchType"] = 1
        params["raceFrom"] = 0
        params["raceTo"] = 15
    elif category == "import":
        # Нерозмитнені / під пригон.
        params["searchType"] = 4
        params["custom"] = 1
    else:
        # «Всі» — увесь ринок (не searchType=1, бо це режим «нові»).
        params["searchType"] = 4

    return params


def _parse_datetime(value: Any) -> datetime:
    """Парсить дату AUTO.RIA. Невідоме значення → далеке минуле (не «зараз»),
    щоб старі/биті дати не проходили фільтр свіжості для Telegram."""
    fallback = datetime(1970, 1, 1, tzinfo=KYIV_TZ)
    if not value:
        return fallback
    if isinstance(value, (int, float)):
        return as_kyiv(datetime.fromtimestamp(value, tz=UTC))
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=KYIV_TZ)
            except ValueError:
                continue
        try:
            return as_kyiv(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            return fallback
    return fallback


def _pick_vin_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def _extract_vin(info: dict[str, Any]) -> str | None:
    for source in (info, info.get("autoData") or {}):
        if not isinstance(source, dict):
            continue
        for key in ("VIN", "vin"):
            vin = _pick_vin_value(source.get(key))
            if vin:
                return vin

    for key in ("checkedVin", "infotechReport"):
        block = info.get(key)
        if not isinstance(block, dict):
            continue
        vin = _pick_vin_value(block.get("vin") or block.get("VIN"))
        if vin:
            return vin

    return None


def _extract_vin_check_url(info: dict[str, Any], auto_id: str) -> str | None:
    checked = info.get("checkedVin")
    if isinstance(checked, dict):
        link = str(checked.get("linkToReport") or "").strip()
        if link:
            return link if link.startswith("http") else f"{AUTO_RIA_SITE_URL}{link}"

    if auto_id:
        return f"{AUTO_RIA_SITE_URL}/vin-check/auto/{auto_id}/"

    return None


def _parse_money(value: Any) -> int:
    """Парсить суму з int/float або рядка на кшталт «12 500»."""
    if value is None or value is False:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        cleaned = (
            value.replace("\u00a0", "")
            .replace("\u202f", "")
            .replace("\u2009", "")
            .replace(" ", "")
            .replace(",", ".")
            .strip()
        )
        if not cleaned:
            return 0
        try:
            return int(round(float(cleaned)))
        except ValueError:
            return 0
    return 0


def _money_from_info(info: dict[str, Any], key: str) -> int:
    """Бере суму з верхнього рівня або з prices[0] (там часто рядки з пробілами)."""
    amount = _parse_money(info.get(key))
    if amount > 0:
        return amount
    prices = info.get("prices")
    if isinstance(prices, list):
        for entry in prices:
            if isinstance(entry, dict):
                amount = _parse_money(entry.get(key))
                if amount > 0:
                    return amount
    return 0


def _listing_price_from_info(info: dict[str, Any]) -> tuple[int, str]:
    """
    Оригінальна ціна оголошення.
    USD з AUTO.RIA має пріоритет — інакше 12 500$ стають 12 389$ через курс 45.
    """
    usd = _money_from_info(info, "USD")
    if usd > 0:
        return usd, "USD"
    eur = _money_from_info(info, "EUR")
    if eur > 0:
        return eur, "EUR"
    uah = _money_from_info(info, "UAH")
    if uah > 0:
        return uah, "UAH"
    return 0, "USD"


def info_to_listing(info: dict[str, Any], *, fotos: Any | None = None) -> ListingOut:
    auto_data = info.get("autoData") or {}
    state_data = info.get("stateData") or {}

    auto_id = str(auto_data.get("autoId") or "")

    link = str(info.get("linkToView") or "")
    url = link if link.startswith("http") else f"{AUTO_RIA_SITE_URL}{link}"

    images = extract_image_urls(info, fotos)

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

    price_amount, price_currency = _listing_price_from_info(info)

    year = int(auto_data.get("year") or 0)
    mileage = int(auto_data.get("raceInt") or 0) * 1000 if auto_data.get("raceInt") else 0

    fuel_raw = str(auto_data.get("fuelName") or "")
    fuel = fuel_raw.split(",")[0].strip() if fuel_raw else ""
    transmission = str(auto_data.get("gearboxName") or "")

    dealer = info.get("dealer") if isinstance(info.get("dealer"), dict) else {}
    seller_type = "dealer" if dealer.get("id") or dealer.get("name") else "private"

    checked_vin = info.get("checkedVin")
    vin_checked = bool(checked_vin.get("isChecked")) if isinstance(checked_vin, dict) else None

    description = str(auto_data.get("description") or info.get("infoBarText") or "").strip() or None

    return ListingOut(
        id=f"auto_ria_{auto_id}",
        source="auto_ria",
        title=title,
        brand=brand,
        model=model,
        year=year,
        price=price_amount,
        currency=price_currency,
        mileage=mileage,
        fuel=fuel,
        transmission=transmission,
        region=region,
        description=description,
        images=images,
        url=url,
        seller_type=seller_type,
        vin=_extract_vin(info),
        vin_checked=vin_checked,
        vin_check_url=_extract_vin_check_url(info, auto_id),
        source_data=sanitize_source_data(info, fotos),
        price_history=[],
        is_duplicate=False,
        published_at=_parse_datetime(info.get("addDate")),
        found_at=now_kyiv(),
    )


def _listing_published_key(item: ListingOut) -> datetime:
    try:
        return as_kyiv(item.published_at)
    except Exception:
        return datetime(1970, 1, 1, tzinfo=KYIV_TZ)


def sort_listings(items: list[ListingOut], sort_by: str) -> list[ListingOut]:
    from app.services.currency import listing_price_uah

    if sort_by in ("published_desc", "newest"):
        return sorted(items, key=_listing_published_key, reverse=True)
    if sort_by == "price_desc":
        return sorted(
            items,
            key=lambda x: listing_price_uah(x.price, x.currency),
            reverse=True,
        )
    if sort_by == "year_desc":
        return sorted(items, key=lambda x: x.year, reverse=True)
    if sort_by == "mileage_asc":
        return sorted(items, key=lambda x: x.mileage)
    return sorted(items, key=lambda x: listing_price_uah(x.price, x.currency))
