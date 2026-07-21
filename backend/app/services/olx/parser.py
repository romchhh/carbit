from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional, TypeGuard
from urllib.parse import quote, urlencode, urljoin

from bs4 import BeautifulSoup

from app.services.olx.constants import (
    BASE_URL,
    CATEGORY_PATH,
    CONDITION_MAP,
    FUEL_KEYWORDS,
    FUEL_MAP,
    TRANSMISSION_KEYWORDS,
    TRANSMISSION_MAP,
)


@dataclass
class OlxSearchParams:
    brand: Optional[str] = None
    model: Optional[str] = None
    # Людські назви для пост-фільтра (коли URL іде через q-текст)
    brand_label: Optional[str] = None
    model_label: Optional[str] = None
    # Текстовий пошук OLX: /q-zeekr-001/ — для марок без taxonomy-path
    text_query: Optional[str] = None
    region_label: Optional[str] = None
    condition: Optional[str] = None
    city_query: Optional[str] = None
    price_from: Optional[int] = None
    price_to: Optional[int] = None
    currency: str = "UAH"
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    mileage_from: Optional[int] = None
    mileage_to: Optional[int] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    engine_from: Optional[float] = None
    engine_to: Optional[float] = None
    drivetrain: Optional[str] = None
    color: Optional[str] = None
    consumption_from: Optional[float] = None
    consumption_to: Optional[float] = None
    ev_range_from: Optional[int] = None
    ev_range_to: Optional[int] = None
    battery_from: Optional[float] = None
    battery_to: Optional[float] = None
    power_from: Optional[int] = None
    power_to: Optional[int] = None
    seats_from: Optional[int] = None
    seats_to: Optional[int] = None
    max_pages: int = 3
    fetch_details: bool = True
    # OLX «Сортувати за: Найновіші» — search[order]=created_at:desc
    sort_order: str = "created_at:desc"

    def needs_post_filter(self) -> bool:
        return any(
            [
                self.region_label,
                self.city_query,
                self.condition,
                self.price_from is not None,
                self.price_to is not None,
                self.year_from is not None,
                self.year_to is not None,
                self.mileage_from is not None,
                self.mileage_to is not None,
                self.fuel,
                self.transmission,
                self.engine_from is not None,
                self.engine_to is not None,
                self.drivetrain,
                self.color,
                self.consumption_from is not None,
                self.consumption_to is not None,
                self.ev_range_from is not None,
                self.ev_range_to is not None,
                self.battery_from is not None,
                self.battery_to is not None,
                self.power_from is not None,
                self.power_to is not None,
                self.seats_from is not None,
                self.seats_to is not None,
            ]
        )

    def needs_detail_fetch(self) -> bool:
        return any(
            [
                self.drivetrain,
                self.color,
                self.consumption_from is not None,
                self.consumption_to is not None,
                self.ev_range_from is not None,
                self.ev_range_to is not None,
                self.battery_from is not None,
                self.battery_to is not None,
                self.power_from is not None,
                self.power_to is not None,
                self.seats_from is not None,
                self.seats_to is not None,
                self.engine_from is not None,
                self.engine_to is not None,
            ]
        )


@dataclass
class OlxListing:
    listing_id: Optional[str] = None
    title: Optional[str] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    year: Optional[str] = None
    mileage: Optional[str] = None
    city: Optional[str] = None
    published: Optional[str] = None
    url: Optional[str] = None
    photo_url: Optional[str] = None
    promoted: bool = False
    description: Optional[str] = None
    photos: list[str] = field(default_factory=list)
    vin: Optional[str] = None
    specs: dict = field(default_factory=dict)
    raw_params: dict = field(default_factory=dict)


VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")  # legacy; prefer extract_vin
PLACEHOLDER_IMAGE_MARKERS = ("no_thumbnail", "/app/static/")


def is_valid_image_url(url: object) -> TypeGuard[str]:
    if not url or not isinstance(url, str):
        return False
    normalized = url.strip()
    if not normalized.startswith(("http://", "https://")):
        return False
    lowered = normalized.lower()
    return not any(marker in lowered for marker in PLACEHOLDER_IMAGE_MARKERS)


def build_search_url(params: OlxSearchParams, page: int = 1) -> str:
    """Будує URL з path-фільтрів (марка/модель/місто) та безпечних query-параметрів.

    Рік, пробіг, паливо тощо в query OLX часто ламають SSR — їх фільтруємо
    пост-фільтром у passes_olx_filters(). Сортування та валюта в query працюють.

    Якщо марки немає в taxonomy OLX (Zeekr тощо) — text_query → /q-zeekr/ або /q-zeekr-001/.
    """
    from app.services.olx.brand_slugs import (
        brand_uses_olx_text_search,
        resolve_olx_brand_slug,
    )

    path_parts = [CATEGORY_PATH.strip("/")]

    text_q = (params.text_query or "").strip().lower().replace(" ", "-")

    # Захист: навіть якщо вище забули text_query — ніколи не збираємо /zeekr/001/
    brand = (params.brand or "").strip()
    model = (params.model or "").strip()
    brand_hint = (params.brand_label or brand or "").strip()
    if not text_q and brand_hint and brand_uses_olx_text_search(brand_hint):
        brand_q = resolve_olx_brand_slug(brand_hint) or brand.lower()
        if model and re.fullmatch(r"\d+[a-z]?", model, re.IGNORECASE):
            text_q = f"{brand_q}-{model.lower()}"
        else:
            text_q = brand_q.lower().replace(" ", "-")
        # Не чіпаємо params (пост-фільтр лишає brand_label/model_label)

    if text_q:
        # Кирилиця в /q-мерседес/ має бути %-encoded
        path_parts.append("q-" + quote(text_q, safe="-._~"))
    elif brand:
        path_parts.append(quote(brand.lower(), safe="-._~"))
        if model:
            path_parts.append(quote(model.lower(), safe="-._~"))

    path = "/" + "/".join(path_parts) + "/"

    # Місто як q- працює лише разом із brand-path; для text_query фільтруємо місто постфактум
    if params.city_query and not text_q:
        path = path.rstrip("/") + f"/q-{params.city_query.lower().strip()}/"

    query: dict[str, str] = {"currency": (params.currency or "UAH").upper()}
    if params.sort_order:
        query["search[order]"] = params.sort_order
    if page > 1:
        query["page"] = str(page)

    url = urljoin(BASE_URL, path)
    return f"{url}?{urlencode(query)}"


def _extract_id_from_url(url: str) -> Optional[str]:
    match = re.search(r"-ID([A-Za-z0-9]+)\.html", url)
    return match.group(1) if match else None


def _normalize_photo_url(url: object) -> Optional[str]:
    if not is_valid_image_url(url):
        return None
    # OLX API: …/image;s={width}x{height}
    return str(url).replace("{width}", "800").replace("{height}", "600")


def _param_value_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("label", "value", "key", "name"):
            candidate = value.get(key)
            if isinstance(candidate, (str, int, float)) and str(candidate).strip():
                if key == "value" and isinstance(candidate, (int, float)):
                    return str(int(candidate)) if float(candidate).is_integer() else str(candidate)
                return str(candidate).strip()
        return ""
    if isinstance(value, list):
        parts = [_param_value_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    return str(value).strip()


def _price_from_params(params: object) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(params, list):
        return None, None
    for item in params:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or item.get("name") or "").strip().lower()
        if key not in ("price", "ціна", "цена"):
            continue
        value = item.get("value")
        if isinstance(value, dict):
            amount = value.get("value") or value.get("amount")
            currency = value.get("currency") or value.get("currencyCode")
            if amount is not None:
                try:
                    return str(int(float(amount))), _normalize_currency(currency)
                except (TypeError, ValueError):
                    pass
            label = value.get("label")
            if isinstance(label, str) and label.strip():
                return _split_price(label)
        text = _param_value_text(value)
        if text:
            return _split_price(text)
    return None, None


def _price_from_embedded(raw: dict) -> tuple[Optional[str], Optional[str]]:
    price_obj = raw.get("price")
    if isinstance(price_obj, dict):
        regular = price_obj.get("regularPrice") or price_obj.get("displayValue") or price_obj
        if isinstance(regular, dict):
            amount = regular.get("value") or regular.get("amount")
            currency = regular.get("currency") or regular.get("currencyCode") or regular.get("currencySymbol")
        else:
            amount = price_obj.get("value") or price_obj.get("amount")
            currency = price_obj.get("currency") or price_obj.get("currencyCode")
        if amount is not None:
            return str(int(float(amount))), _normalize_currency(currency)
    return _price_from_params(raw.get("params"))


def _photo_from_embedded(raw: dict) -> Optional[str]:
    photos = raw.get("photos") or raw.get("images") or []
    if isinstance(photos, list):
        for item in photos:
            if isinstance(item, str):
                normalized = _normalize_photo_url(item)
                if normalized:
                    return normalized
            if isinstance(item, dict):
                for key in ("link", "url", "src", "original"):
                    candidate = _normalize_photo_url(item.get(key))
                    if candidate:
                        return candidate
    return None


def _params_from_embedded(params: object) -> tuple[Optional[str], Optional[str], dict[str, str]]:
    year: Optional[str] = None
    mileage: Optional[str] = None
    specs: dict[str, str] = {}
    if not isinstance(params, list):
        return year, mileage, specs

    for item in params:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("key") or "").strip()
        value = _param_value_text(item.get("value") if "value" in item else item.get("normalizedValue"))
        if not name or not value:
            continue
        key = str(item.get("key") or "").strip().lower()
        if key == "price":
            continue
        specs[name] = value
        name_low = name.lower()
        if year is None and ("рік" in name_low or name_low == "year" or key in ("motor_year", "year")):
            match = re.search(r"(19[5-9]\d|20[0-4]\d)", value)
            if match:
                year = match.group(1)
        if mileage is None and ("пробіг" in name_low or "mileage" in name_low or "mileage" in key):
            mileage = value
    return year, mileage, specs


def _normalize_api_offer(raw: dict) -> dict:
    """API /api/v1/offers/ → формат ближчий до __PRERENDERED_STATE__."""
    if not isinstance(raw, dict):
        return {}
    if raw.get("createdTime") or raw.get("urlPath"):
        return raw

    normalized = dict(raw)
    if "created_time" in raw and "createdTime" not in normalized:
        normalized["createdTime"] = raw.get("created_time")
    if "last_refresh_time" in raw and "lastRefreshTime" not in normalized:
        normalized["lastRefreshTime"] = raw.get("last_refresh_time")
    if "external_url" in raw and "externalUrl" not in normalized:
        normalized["externalUrl"] = raw.get("external_url")

    promotion = raw.get("promotion")
    if isinstance(promotion, dict):
        normalized["isHighlighted"] = bool(
            promotion.get("highlighted") or promotion.get("top_ad") or promotion.get("urgent")
        )
        normalized["isPromoted"] = bool(promotion.get("top_ad") or promotion.get("premium_ad_page"))

    return normalized


def parse_offers_api_payload(payload: object) -> list[OlxListing]:
    """Парсить JSON відповіді GET /api/v1/offers/."""
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    listings: list[OlxListing] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        listing = _listing_from_embedded(_normalize_api_offer(row))
        if not listing or not listing.listing_id or listing.listing_id in seen:
            continue
        seen.add(listing.listing_id)
        listings.append(listing)
    return listings


def build_offers_api_query(params: OlxSearchParams) -> str:
    """Текст для OLX offers API з поточних search params."""
    if params.text_query:
        return re.sub(r"[-_]+", " ", params.text_query).strip()
    parts: list[str] = []
    brand = (params.brand_label or params.brand or "").strip()
    model = (params.model_label or params.model or "").strip()
    if brand:
        parts.append(brand)
    if model:
        parts.append(model)
    return " ".join(parts).strip()


def _normalize_currency(value: object) -> Optional[str]:
    if not value:
        return None
    text = str(value).upper()
    if text in ("UAH", "ГРН", "₴"):
        return "UAH"
    if text in ("USD", "$"):
        return "USD"
    if text in ("EUR", "€"):
        return "EUR"
    return None


def _city_from_embedded(raw: dict) -> Optional[str]:
    location = raw.get("location")
    if not isinstance(location, dict):
        return None

    # Новий формат OLX (2026): flat keys cityName / regionName / pathName
    for key in ("cityName", "city_name", "pathName", "path_name"):
        value = location.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    city = location.get("city")
    if isinstance(city, dict):
        name = city.get("name") or city.get("normalizedName")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(city, str) and city.strip():
        return city.strip()

    region = location.get("region") or location.get("regionName")
    if isinstance(region, dict):
        name = region.get("name") or region.get("normalizedName")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(region, str) and region.strip():
        return region.strip()

    name = location.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def _location_parts_from_listing(listing: OlxListing) -> dict[str, str]:
    parts: dict[str, str] = {}
    if listing.city:
        parts["city"] = str(listing.city).strip().lower()
    raw = listing.raw_params if isinstance(listing.raw_params, dict) else {}
    location = raw.get("location")
    if not isinstance(location, dict):
        return parts

    for dest, keys in (
        ("city", ("cityName", "city_name")),
        ("region", ("regionName", "region_name")),
        ("district", ("districtName", "district_name")),
        ("path", ("pathName", "path_name")),
    ):
        for key in keys:
            value = location.get(key)
            if isinstance(value, str) and value.strip():
                parts[dest] = value.strip().lower()
                break

    city = location.get("city")
    if "city" not in parts:
        if isinstance(city, dict):
            for key in ("name", "normalizedName"):
                value = city.get(key)
                if isinstance(value, str) and value.strip():
                    parts["city"] = value.strip().lower()
                    break
        elif isinstance(city, str) and city.strip():
            parts["city"] = city.strip().lower()

    region = location.get("region")
    if "region" not in parts and isinstance(region, dict):
        for key in ("name", "normalizedName"):
            value = region.get(key)
            if isinstance(value, str) and value.strip():
                parts["region"] = value.strip().lower()
                break
    return parts


def _location_blob_from_listing(listing: OlxListing) -> str:
    parts = _location_parts_from_listing(listing)
    return " ".join(parts.values())


# city_query slug → ключові слова для пост-фільтра регіону (text_query не додає /q-city/)
_KYIV_CITY_NAMES = ("київ", "киев", "kyiv", "kiev")
_KYIV_OBLAST_CITIES = (
    "бровар",
    "біла церкв",
    "белая церк",
    "ірпін",
    "ирпен",
    "буча",
    "фастів",
    "фастов",
    "вишгород",
    "обухів",
    "обухов",
    "боярк",
    "вишнев",
    "васильк",
)


def _city_name_is_kyiv(city: str) -> bool:
    """True лише для м. Київ, не для «Київська область» / Боярка."""
    if not city:
        return False
    # «Київ, Шевченківський» / «Київ»
    head = city.split(",")[0].strip()
    for name in _KYIV_CITY_NAMES:
        if head == name or head.startswith(name + " "):
            return True
    return False


def _listing_region_text(listing: OlxListing) -> str:
    parts = _location_parts_from_listing(listing)
    if parts:
        return ", ".join(parts.values())
    city = (listing.city or "").strip()
    return city


def _passes_region_filter(listing: OlxListing, region_label: str | None) -> bool:
    from app.services.search.region_match import listing_region_matches_filter

    if not region_label:
        return True
    return listing_region_matches_filter(_listing_region_text(listing), region_label)


def _passes_city_query(listing: OlxListing, city_query: str | None) -> bool:
    if not city_query:
        return True
    parts = _location_parts_from_listing(listing)
    if not parts:
        # Немає локації в картці — не відсікаємо (краще показати, ніж втратити)
        return True

    key = city_query.strip().lower()
    city = parts.get("city") or ""
    region = parts.get("region") or ""
    path = parts.get("path") or ""
    blob = " ".join(parts.values())

    if key == "kyiv":
        return _city_name_is_kyiv(city)

    if key == "київська-область":
        if "київськ" in region or "киевск" in region:
            return True
        if "київськ" in path or "киевск" in path:
            return True
        return any(token in city or token in blob for token in _KYIV_OBLAST_CITIES)

    needle = key.replace("-", " ").strip()
    return bool(needle) and (needle in blob or key in blob)


def _listing_from_embedded(raw: dict) -> Optional[OlxListing]:
    listing_id = raw.get("id")
    url = (
        raw.get("url")
        or raw.get("urlPath")
        or raw.get("slug")
        or raw.get("friendlyUrl")
        or raw.get("externalUrl")
    )
    if listing_id is None or not url:
        return None

    listing_id = str(listing_id)
    full_url = urljoin(BASE_URL, url) if str(url).startswith("/") else str(url)
    if "olx.ua" not in full_url and not str(url).startswith("/"):
        return None

    price, currency = _price_from_embedded(raw)
    year, mileage, specs = _params_from_embedded(raw.get("params"))
    # published_at = перша публікація (createdTime). lastRefreshTime — окремо в raw_params.
    created = raw.get("createdTime") or raw.get("created_time")

    title = raw.get("title")
    if not year and title:
        match = re.search(r"(19[5-9]\d|20[0-4]\d)", str(title))
        if match:
            year = match.group(1)

    return OlxListing(
        listing_id=listing_id,
        title=str(title) if title else None,
        url=full_url,
        price=price,
        currency=currency,
        year=year,
        mileage=mileage,
        city=_city_from_embedded(raw),
        published=str(created) if created else None,
        photo_url=_photo_from_embedded(raw),
        promoted=bool(raw.get("isHighlighted") or raw.get("promoted") or raw.get("isPromoted")),
        specs=specs,
        raw_params=raw if isinstance(raw, dict) else {},
    )


def _parse_mileage_text(params_text: str) -> Optional[str]:
    if not params_text:
        return None
    match = re.search(r"([\d\s]+)\s*тис\.?\s*км", params_text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "") + " тис.км"
    match = re.search(r"([\d\s]{4,7})\s*км", params_text, re.IGNORECASE)
    if match:
        digits = re.sub(r"\s", "", match.group(1))
        return f"{digits} км"
    return None


def _parse_json_assignment(html: str, marker: str) -> object | None:
    """Parse `window.FOO = {...}` or `window.FOO = "{...}"`."""
    match = re.search(re.escape(marker) + r"\s*=\s*", html)
    if not match:
        return None
    start = match.end()
    while start < len(html) and html[start] in " \t\n\r":
        start += 1
    if start >= len(html):
        return None

    try:
        if html[start] == '"':
            # JSON-encoded string payload
            decoder = json.JSONDecoder()
            raw_string, _ = decoder.raw_decode(html[start:])
            if isinstance(raw_string, str):
                return json.loads(raw_string)
            return raw_string
        if html[start] == "{":
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(html[start:])
            return data
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    return None


def _collect_ad_dicts(node: object, results: list[dict]) -> None:
    if isinstance(node, dict):
        has_id = node.get("id") is not None
        has_title = bool(node.get("title"))
        has_url = bool(
            node.get("url")
            or node.get("slug")
            or node.get("urlPath")
            or node.get("friendlyUrl")
        )
        has_time = bool(
            node.get("createdTime")
            or node.get("lastRefreshTime")
            or node.get("created_time")
            or node.get("last_refresh_time")
        )
        if has_id and has_title and (has_url or has_time):
            results.append(node)
        for value in node.values():
            _collect_ad_dicts(value, results)
    elif isinstance(node, list):
        for item in node:
            _collect_ad_dicts(item, results)


def _try_extract_embedded_json(html: str) -> list[dict]:
    """
    OLX search HTML: раніше __NEXT_DATA__, зараз window.__PRERENDERED_STATE__.
    """
    results: list[dict] = []

    for marker in (
        "window.__PRERENDERED_STATE__",
        "window.__NEXT_DATA__",
    ):
        data = None
        if marker.startswith("window."):
            data = _parse_json_assignment(html, marker)
        if data is None and marker == "window.__NEXT_DATA__":
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    data = None
        if data is None:
            continue
        _collect_ad_dicts(data, results)
        if results:
            break

    # Prefer richer ad objects (with timestamps) first, keep order otherwise.
    results.sort(
        key=lambda item: (
            0
            if (item.get("lastRefreshTime") or item.get("createdTime"))
            else 1,
            str(item.get("id") or ""),
        )
    )

    # Deduplicate by id
    seen: set[str] = set()
    unique: list[dict] = []
    for item in results:
        listing_id = str(item.get("id") or "")
        if not listing_id or listing_id in seen:
            continue
        seen.add(listing_id)
        unique.append(item)
    return unique


def _listings_from_json_ld(html: str) -> list[OlxListing]:
    """Fallback: schema.org AggregateOffer у application/ld+json (коли state порожній)."""
    listings: list[OlxListing] = []
    seen: set[str] = set()
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        raw = match.group(1).strip()
        if not raw or "AggregateOffer" not in raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "Product":
            continue
        offers_wrap = data.get("offers")
        if not isinstance(offers_wrap, dict):
            continue
        offers = offers_wrap.get("offers") or offers_wrap.get("itemListElement") or []
        if not isinstance(offers, list):
            continue
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            url = offer.get("url")
            title = offer.get("name")
            if not url or not title:
                continue
            listing_id = _extract_id_from_url(str(url))
            if not listing_id or listing_id in seen:
                continue
            seen.add(listing_id)
            price_val = offer.get("price")
            currency = _normalize_currency(offer.get("priceCurrency"))
            area = offer.get("areaServed")
            city = None
            if isinstance(area, dict):
                city = area.get("name")
            elif isinstance(area, str):
                city = area
            images = offer.get("image") or []
            photo = None
            if isinstance(images, list):
                for img in images:
                    if is_valid_image_url(img):
                        photo = img
                        break
            elif is_valid_image_url(images):
                photo = images
            year = None
            year_match = re.search(r"(19[5-9]\d|20[0-4]\d)", str(title))
            if year_match:
                year = year_match.group(1)
            listings.append(
                OlxListing(
                    listing_id=listing_id,
                    title=str(title),
                    url=str(url),
                    price=str(int(float(price_val))) if price_val is not None else None,
                    currency=currency,
                    year=year,
                    city=str(city).strip() if city else None,
                    photo_url=photo,
                    published=str(offer.get("priceValidUntil") or "") or None,
                )
            )
    return listings


def parse_listing_page(html: str) -> list[OlxListing]:
    listings: list[OlxListing] = []
    seen_ids: set[str] = set()

    embedded = _try_extract_embedded_json(html)
    for raw in embedded:
        listing = _listing_from_embedded(raw)
        if not listing or not listing.listing_id or listing.listing_id in seen_ids:
            continue
        seen_ids.add(listing.listing_id)
        listings.append(listing)

    if listings:
        return listings

    for listing in _listings_from_json_ld(html):
        if not listing.listing_id or listing.listing_id in seen_ids:
            continue
        seen_ids.add(listing.listing_id)
        listings.append(listing)

    if listings:
        return listings

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-testid="l-card"]')
    if not cards:
        cards = soup.select('[data-cy="l-card"]')
    if not cards:
        # Fallback: title nodes → піднімаємось до картки, якщо є
        title_nodes = soup.select('[data-testid="ad-card-title"]')
        recovered = []
        for node in title_nodes:
            parent = node.find_parent(attrs={"data-testid": "l-card"}) or node.find_parent(
                attrs={"data-cy": "l-card"}
            )
            recovered.append(parent or node)
        cards = recovered
    if not cards:
        cards = soup.select('a[href*="obyavlenie"]')

    for card in cards:
        try:
            listing = _parse_single_card(card)
            if listing and listing.url:
                if listing.listing_id and listing.listing_id in seen_ids:
                    continue
                if listing.listing_id:
                    seen_ids.add(listing.listing_id)
                listings.append(listing)
        except Exception:
            continue

    return listings

def _parse_single_card(card) -> Optional[OlxListing]:
    link_tag = card if card.name == "a" else card.find("a", href=True)
    if not link_tag or not link_tag.get("href"):
        # OLX інколи кладе посилання в data-testid="card-title-link"
        link_tag = card.select_one('a[data-testid="card-title-link"][href]') or card.select_one(
            'a[href*="obyavlenie"]'
        )
    if not link_tag or not link_tag.get("href"):
        return None

    url = urljoin(BASE_URL, link_tag["href"])
    listing_id = _extract_id_from_url(url)

    is_promoted = bool(
        card.select_one('[data-testid="adCard-featured"]')
        or "promoted" in url
        or card.find(string=re.compile("TOP|Промо", re.IGNORECASE))
    )

    title_tag = (
        card.select_one('[data-testid="card-title-link"]')
        or card.select_one('[data-testid="ad-card-title"] h4')
        or card.select_one('[data-testid="ad-card-title"] h6')
        or card.select_one('[data-testid="ad-title"]')
        or card.select_one("h4")
        or card.select_one("h6")
        or link_tag
    )
    title = title_tag.get_text(strip=True) if title_tag else None
    # ad-card-title інколи містить і ціну — беремо лише перший рядок / h4
    if title and title_tag is not None and title_tag.get("data-testid") == "ad-card-title":
        inner = title_tag.select_one("h4, h6, a")
        if inner:
            title = inner.get_text(strip=True)

    price_tag = card.select_one('[data-testid="ad-price"]')
    price_text = price_tag.get_text(strip=True) if price_tag else None
    price, currency = _split_price(price_text)

    location_tag = card.select_one('[data-testid="location-date"]')
    city, published = _split_location_date(
        location_tag.get_text(strip=True) if location_tag else None
    )

    params_text = ""
    params_tag = card.select_one('[data-testid="ad-params"]') or card.select_one(
        '[data-testid="listing-parameters"]'
    )
    if params_tag:
        params_text = params_tag.get_text(" ", strip=True)
    # Сучасна видача: параметри інколи лише в іконках/тексті поруч із title
    if not params_text:
        params_text = " ".join(
            node.get_text(" ", strip=True)
            for node in card.select('[data-testid*="param"], [class*="param"]')
            if node.get_text(strip=True)
        )

    year_match = re.search(r"(19[5-9]\d|20[0-4]\d)", params_text or title or "")
    year = year_match.group(1) if year_match else None

    mileage = _parse_mileage_text(params_text or "")

    img_tag = card.select_one("img")
    photo_url = None
    if img_tag:
        for attr in ("src", "data-src", "data-lazy-src"):
            candidate = img_tag.get(attr)
            if is_valid_image_url(candidate):
                photo_url = candidate
                break
        if not photo_url:
            srcset = img_tag.get("srcset") or ""
            for part in srcset.split(","):
                candidate = part.strip().split(" ")[0]
                if is_valid_image_url(candidate):
                    photo_url = candidate
                    break

    return OlxListing(
        listing_id=listing_id,
        title=title,
        price=price,
        currency=currency,
        year=year,
        mileage=mileage,
        city=city,
        published=published,
        url=url,
        photo_url=photo_url,
        promoted=is_promoted,
    )


def _split_price(price_text: Optional[str]):
    if not price_text:
        return None, None
    text = price_text.replace("\xa0", " ").strip()
    lowered = text.lower()
    currency = None
    if "грн" in lowered:
        currency = "UAH"
    elif "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"

    chunk = lowered.split("грн")[0] if "грн" in lowered else text
    chunk = chunk.replace(" ", "").replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", chunk)
    if not match:
        return None, currency
    amount = int(round(float(match.group(1))))
    if amount <= 0:
        return None, currency
    return str(amount), currency


def _split_location_date(text: Optional[str]):
    if not text:
        return None, None
    normalized = text.replace("\xa0", " ").strip()
    for sep in (" - ", " – ", " — ", " • ", " · "):
        if sep in normalized:
            left, right = normalized.split(sep, 1)
            return left.strip(), right.strip()
    return normalized, None


def parse_listing_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    description_tag = soup.select_one('[data-testid="ad_description"]') or soup.select_one(
        '[data-cy="ad_description"]'
    )
    description = description_tag.get_text("\n", strip=True) if description_tag else None

    photos: list[str] = []
    gallery = soup.select('[data-testid="ad-photo"] img, [data-testid="swiper-wrapper"] img')
    for img in gallery:
        for attr in ("src", "data-src", "data-lazy-src"):
            src = img.get(attr)
            if is_valid_image_url(src) and src not in photos:
                photos.append(src)
    if not photos:
        og_image = soup.select_one('meta[property="og:image"]')
        content = og_image.get("content") if og_image else None
        if is_valid_image_url(content):
            photos.append(content)

    price_tag = soup.select_one('[data-testid="ad-price"]') or soup.select_one('[data-cy="ad-price"]')
    price_text = price_tag.get_text(strip=True) if price_tag else None
    price, currency = _split_price(price_text)

    specs: dict[str, str | list[str]] = {}
    param_rows = soup.select('[data-testid="ad-parameters-container"] p, [data-testid="ad-parameter"]')
    for row in param_rows:
        text = row.get_text(" ", strip=True)
        if ":" in text:
            key, _, value = text.partition(":")
            specs[key.strip()] = value.strip()
        elif text:
            existing = specs.get("_unlabeled")
            if isinstance(existing, list):
                existing.append(text)
            else:
                specs["_unlabeled"] = [text]

    vin = None
    for value in specs.values():
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            if not isinstance(item, str):
                continue
            from app.services.vin import extract_vin

            vin = extract_vin(item)
            if vin:
                break
        if vin:
            break
    if not vin and description:
        from app.services.vin import extract_vin

        vin = extract_vin(description)
    if not vin:
        from app.services.vin import extract_vin

        title_tag = soup.select_one("h1") or soup.select_one('[data-testid="ad-title"]')
        title_text = title_tag.get_text(" ", strip=True) if title_tag else None
        vin = extract_vin(title_text, soup.get_text("\n", strip=True)[:4000])

    posted_tag = (
        soup.select_one('[data-testid="ad-posted-at"]')
        or soup.select_one('[data-cy="ad-posted-at"]')
        or soup.select_one('[data-testid="location-date"]')
    )
    # separator=" " — інакше «Опубліковано»+«сьогодні…» зливається в «Опублікованосьогодні»
    published = posted_tag.get_text(" ", strip=True) if posted_tag else None

    # ISO-час з __PRERENDERED_STATE__ на детальній сторінці (надійніше за відносний текст)
    last_refresh_time = None
    created_time = None
    for raw in _try_extract_embedded_json(html):
        last_refresh_time = (
            raw.get("lastRefreshTime")
            or raw.get("last_refresh_time")
            or last_refresh_time
        )
        created_time = raw.get("createdTime") or raw.get("created_time") or created_time
        if last_refresh_time or created_time:
            break

    return {
        "description": description,
        "photos": photos,
        "vin": vin,
        "specs": specs,
        "price": price,
        "currency": currency,
        "published": published,
        "lastRefreshTime": last_refresh_time,
        "createdTime": created_time,
    }


def _spec_text(specs: dict, *keys: str) -> str:
    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        if any(key.lower() in spec_key.lower() for key in keys):
            return spec_value.strip()
    return ""


def _is_better_published(candidate: str | None, current: str | None) -> bool:
    """Чи варто замінити current на candidate (пріоритет ISO > відносний текст)."""
    if not candidate:
        return False
    from app.services.olx.dates import _parse_iso_datetime, parse_olx_published_text

    cand_iso = _parse_iso_datetime(candidate)
    cur_iso = _parse_iso_datetime(current) if current else None
    if cand_iso and not cur_iso:
        return True
    if cand_iso and cur_iso:
        return False
    if current and (cur_iso or parse_olx_published_text(current)):
        # Уже є щось парсабельне — не затираємо злитим «Опублікованосьогодні»
        return False
    return bool(parse_olx_published_text(candidate) or _parse_iso_datetime(candidate))


def apply_details_to_listing(listing: OlxListing, details: dict) -> None:
    if not details:
        return

    listing.description = details.get("description") or listing.description
    listing.vin = details.get("vin") or listing.vin
    if not listing.vin:
        from app.services.vin import extract_vin

        listing.vin = extract_vin(
            listing.title,
            listing.description,
            " ".join(str(v) for v in (listing.specs or {}).values() if isinstance(v, str)),
        )
    listing.specs = {**(listing.specs or {}), **(details.get("specs") or {})}

    photos = [url for url in details.get("photos", []) if is_valid_image_url(url)]
    if photos:
        listing.photos = photos
        listing.photo_url = photos[0]

    if not listing.price and details.get("price"):
        listing.price = details.get("price")
    if not listing.currency and details.get("currency"):
        listing.currency = details.get("currency")

    if listing.raw_params is None:
        listing.raw_params = {}
    for key in ("lastRefreshTime", "createdTime"):
        value = details.get(key)
        if value and key not in listing.raw_params:
            listing.raw_params[key] = value

    # Не підміняємо «Опубліковано…» / createdTime на lastRefreshTime (підняття ≠ дата публікації).
    created_iso = details.get("createdTime")
    if _is_better_published(created_iso, listing.published):
        listing.published = str(created_iso)
    elif _is_better_published(details.get("published"), listing.published):
        listing.published = details.get("published")
    elif not listing.published and details.get("lastRefreshTime"):
        # Немає created/тексту — лишаємо refresh лише як крайній fallback у raw_params.
        pass

    specs = listing.specs or {}
    if not listing.year:
        listing.year = _spec_text(specs, "рік", "year") or listing.year
    if not listing.mileage:
        listing.mileage = _spec_text(specs, "пробіг", "mileage") or listing.mileage

    fuel = _spec_text(specs, "палив", "fuel")
    if fuel and "палив" not in (listing.title or "").lower():
        listing.raw_params.setdefault("fuel", fuel)

    transmission = _spec_text(specs, "короб", "transmission", "кпп")
    if transmission:
        listing.raw_params.setdefault("transmission", transmission)


def listing_needs_enrichment(listing: OlxListing, params: OlxSearchParams | None = None) -> bool:
    """Деталі сторінки — лише коли без них неможливо застосувати фільтри."""
    if not listing.url:
        return False
    if params and params.needs_detail_fetch():
        return True
    # Ціна потрібна для price_from/price_to; рік/фото для списку не тягнемо окремо
    if params and (params.price_from is not None or params.price_to is not None):
        if not _listing_price(listing):
            return True
    if params and (params.seats_from is not None or params.seats_to is not None):
        specs = listing.specs or {}
        if not _spec_number(specs, "місць", "міс", "seat", "сидяч"):
            return True
    return False


def _spec_number(specs: dict, *keys: str) -> Optional[float]:
    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        if any(key.lower() in spec_key.lower() for key in keys):
            match = re.search(r"[\d]+[.,]?\d*", spec_value.replace(" ", ""))
            if match:
                return float(match.group(0).replace(",", "."))
    return None


def html_looks_like_results_page(html: str) -> bool:
    markers = (
        'data-testid="l-card"',
        'data-cy="l-card"',
        'data-testid="ad-card-title"',
        'id="__NEXT_DATA__"',
        "window.__PRERENDERED_STATE__",
        "/d/uk/obyavlenie/",
        "AggregateOffer",
    )
    return any(marker in html for marker in markers)


def _listing_price(listing: OlxListing) -> int | None:
    if not listing.price:
        return None
    digits = re.sub(r"[^\d]", "", str(listing.price))
    if not digits:
        return None
    return int(digits)


def _listing_price_uah(listing: OlxListing) -> int | None:
    raw = _listing_price(listing)
    if raw is None:
        return None
    from app.services.currency import to_uah

    return to_uah(raw, listing.currency)


def _listing_year(listing: OlxListing) -> int | None:
    if listing.year:
        match = re.search(r"\d{4}", str(listing.year))
        if match:
            return int(match.group(0))
    blob = f"{listing.title or ''} {listing.raw_params}"
    match = re.search(r"(19[5-9]\d|20[0-4]\d)", blob)
    return int(match.group(1)) if match else None


def _listing_mileage_km(listing: OlxListing) -> int | None:
    if listing.mileage:
        parsed = _parse_mileage_km_value(str(listing.mileage))
        if parsed:
            return parsed

    specs = listing.specs or {}
    spec_value = _spec_text(specs, "пробіг", "mileage")
    if spec_value:
        parsed = _parse_mileage_km_value(spec_value)
        if parsed:
            return parsed

    blob = f"{listing.title or ''} {listing.raw_params}"
    match = re.search(r"([\d\s]+)\s*тис\.?\s*км", blob, re.IGNORECASE)
    if match:
        return int(re.sub(r"\s", "", match.group(1)) or "0") * 1000
    match = re.search(r"([\d\s]{4,7})\s*км", blob, re.IGNORECASE)
    if match:
        return int(re.sub(r"\s", "", match.group(1)) or "0")
    return None


def _parse_mileage_km_value(value: str) -> int | None:
    match = re.search(r"([\d\s]+)\s*тис", value, re.IGNORECASE)
    if match:
        return int(re.sub(r"\s", "", match.group(1)) or "0") * 1000
    match = re.search(r"([\d\s]{4,7})\s*км", value, re.IGNORECASE)
    if match:
        return int(re.sub(r"\s", "", match.group(1)) or "0")
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return None
    amount = int(digits)
    if amount > 1000:
        return amount
    return amount * 1000


def _listing_text_blob(listing: OlxListing) -> str:
    parts = [listing.title or "", listing.description or ""]
    if isinstance(listing.raw_params, dict):
        parts.extend(str(v) for v in listing.raw_params.values() if isinstance(v, str))
    parts.extend(str(v) for v in (listing.specs or {}).values() if isinstance(v, str))
    return " ".join(parts).lower()


def _matches_keyword_filter(text: str, key: str | None, mapping: dict[str, tuple[str, ...]]) -> bool:
    if not key:
        return True
    keywords = mapping.get(key.lower())
    if not keywords:
        return True
    return any(word in text for word in keywords)


# Аліаси марки в заголовку (text_query /q-.../)
_BRAND_TITLE_ALIASES: dict[str, tuple[str, ...]] = {
    "li auto": ("li auto", "lixiang", "li xiang", "li-auto", "лі авто", "ли авто"),
    "li": ("li auto", "lixiang", "li xiang", "li-auto"),
    "xpeng": ("xpeng", "x peng", "xiao peng"),
    "lynk & co": ("lynk", "lynk&co", "lynk and co"),
    "lynk and co": ("lynk", "lynk&co", "lynk and co"),
    "great wall motor": ("great wall", "gwm", "haval"),
    "zeekr": ("zeekr", "зікр", "зикр", "зеекр"),
    "mercedes-benz": (
        "mercedes-benz",
        "mercedes benz",
        "mercedes",
        "mersedes",
        "mersedes-benz",
        "мерседес-бенц",
        "мерседес бенц",
        "мерседес",
        "мерс",
    ),
    "mercedes benz": (
        "mercedes-benz",
        "mercedes benz",
        "mercedes",
        "mersedes",
        "мерседес",
        "мерс",
    ),
    "volkswagen": ("volkswagen", "vw", "фольксваген"),
    "bmw": ("bmw", "бмв"),
    "toyota": ("toyota", "тойота"),
    "land rover": ("land rover", "land-rover", "range rover", "ленд ровер"),
    "land-rover": ("land rover", "land-rover", "range rover", "ленд ровер"),
    "tesla": ("tesla", "тесла", "tesla motors"),
}

# Regex-аліаси марки (typo / змішана кирилиця-latin у заголовках OLX)
_BRAND_TITLE_REGEX: dict[str, tuple[str, ...]] = {
    "tesla": (r"t[eеё\u0435\u0451]sla", r"тесла", r"te[s5]la"),
}

# Кирилиця → latin для змішаних написань (ТЕSLA, Аudi …)
_TITLE_HOMOGLYPHS = str.maketrans(
    {
        "а": "a",
        "А": "a",
        "в": "b",
        "В": "b",
        "е": "e",
        "Е": "e",
        "к": "k",
        "К": "k",
        "м": "m",
        "М": "m",
        "о": "o",
        "О": "o",
        "р": "p",
        "Р": "p",
        "с": "c",
        "С": "c",
        "т": "t",
        "Т": "t",
        "у": "y",
        "У": "y",
        "х": "x",
        "Х": "x",
    }
)


def _normalize_title_for_match(text: str) -> str:
    """Latinize лише змішані в одному слові кирилиця+latin (ТЕSLA), не чисту «Тесла»."""
    if not text:
        return text
    if not re.search(r"[A-Za-z]", text) or not re.search(r"[\u0400-\u04FF]", text):
        return text
    words = text.split()
    out: list[str] = []
    for word in words:
        if re.search(r"[A-Za-z]", word) and re.search(r"[\u0400-\u04FF]", word):
            out.append(word.translate(_TITLE_HOMOGLYPHS))
        else:
            out.append(word)
    return " ".join(out)

# Запчастини / неавто, які OLX підмішує в /q-/ навіть у категорії легкових
_NON_CAR_TITLE_RE = re.compile(
    r"(?i)(?:"
    r"коврик|килимок|килимки|автоковрик|eva\b|єва\b|"
    r"фара\b|бампер|крило\b|капот|решітк|решетк|"
    r"запчаст|розборк|фаркоп|обвес|спойлер|дифузор|"
    r"шина\b|шини\b|диск[аи]\b|проставк|"
    r"скутер|мопед|квадроцикл|"
    r"квартир|жк\s|житлов|"
    r"українізац|русифікац|"
    r"зарядн\w*\s+станц|конструктор"
    r")"
)

_PARTS_SPEC_MARKERS = (
    "тип запчастини",
    "тип килимків",
    "код запчастини",
)

# Категорії OLX поза легковими авто (підмішані extended search)
_NON_CAR_CATEGORY_IDS = frozenset(
    {
        1463,  # диски
        1459,  # шини
        1941,  # електроскутери
        2158,  # килимки
        2186,  # фаркопи
        2418,  # бампери
        2421,  # захист двигуна
        2458,  # запчастини GW/Haval
        2515,  # проставки
        2544,  # фари
    }
)


def _brand_aliases(brand: str) -> tuple[str, ...]:
    key = brand.strip().lower()
    aliases = _BRAND_TITLE_ALIASES.get(key)
    if aliases:
        return aliases
    return (key,) if key else ()


def _title_has_brand(title: str, brand: str) -> bool:
    key = brand.strip().lower()
    normalized = _normalize_title_for_match(title)
    for pattern in _BRAND_TITLE_REGEX.get(key, ()):
        if re.search(pattern, normalized, re.IGNORECASE):
            return True
        if re.search(pattern, title, re.IGNORECASE):
            return True
    for alias in _brand_aliases(brand):
        if " " in alias or "-" in alias:
            if alias in title or alias in normalized:
                return True
            continue
        if re.search(rf"(?<![\w]){re.escape(alias)}(?![\w])", normalized, re.IGNORECASE):
            return True
        if re.search(rf"(?<![\w]){re.escape(alias)}(?![\w])", title, re.IGNORECASE):
            return True
    return False


def _title_has_model(title: str, model: str, *, brand: str | None = None) -> bool:
    model_l = model.strip().lower()
    if not model_l:
        return True
    if re.fullmatch(r"\d+[a-z]?", model_l):
        return bool(
            re.search(rf"(?<![\w]){re.escape(model_l)}(?![\w])", title, re.IGNORECASE)
        )
    if model_l in title:
        return True
    brand_l = (brand or "").strip().lower()
    brand_slug = ""
    if brand_l:
        from app.services.olx.brand_slugs import resolve_olx_brand_slug

        brand_slug = resolve_olx_brand_slug(brand_l)
    # Tesla «Model S» → «S 100D», «model-s plaid», «TESSLA S 100 KWH», «Тесла модел S»
    model_word = re.fullmatch(r"model\s+([a-z0-9]+)", model_l)
    if model_word and brand_slug == "tesla":
        token = model_word.group(1)
        tesla_patterns = (
            rf"model[\s\-]?{re.escape(token)}\b",
            rf"модел[\s\-]?{re.escape(token)}\b",
            rf"модель[\s\-]?{re.escape(token)}\b",
            rf"tesla[\s\-]?{re.escape(token)}\b",
            rf"тесла[\s\-]?{re.escape(token)}\b",
            rf"\b{re.escape(token)}\b.*(?:plaid|long range|performance|dual motor|kwh|перформанс|100d|75d|90d|85d|60d|p100d)",
        )
        for pattern in tesla_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return True
    # E-Class / C-Class → «E 220», «E-Class», «E-клас», «C200»
    class_m = re.fullmatch(r"([a-z])-class", model_l)
    if class_m:
        letter = class_m.group(1)
        if re.search(
            rf"(?<![\w]){letter}(?:[\s\-]?class|[\s\-]?клас[сау]?|[\s\-]?\d{{2,3}})(?![\w])",
            title,
            re.IGNORECASE,
        ):
            return True
    # J7 / C5 / X3 → «Jaecoo 7», «Omoda C5»
    letter_num = re.fullmatch(r"([a-z]+)(\d+[a-z]?)", model_l)
    if letter_num:
        letter, num = letter_num.group(1), letter_num.group(2)
        if re.search(
            rf"(?<![\w]){re.escape(letter)}-?{re.escape(num)}(?![\w])",
            title,
            re.IGNORECASE,
        ):
            return True
        brand_l = (brand or "").strip().lower()
        if brand_l and re.search(
            rf"(?<![\w]){re.escape(brand_l)}\s+{re.escape(num)}(?![\w])",
            title,
            re.IGNORECASE,
        ):
            return True
    return False


def _is_non_car_listing(listing: OlxListing) -> bool:
    title = listing.title or ""
    if _NON_CAR_TITLE_RE.search(title):
        return True

    specs = listing.specs or {}
    spec_keys = " ".join(str(k).lower() for k in specs)
    if any(marker in spec_keys for marker in _PARTS_SPEC_MARKERS):
        return True

    raw = listing.raw_params if isinstance(listing.raw_params, dict) else {}
    category = raw.get("category")
    if isinstance(category, dict):
        cat_id = category.get("id")
        if isinstance(cat_id, int) and cat_id in _NON_CAR_CATEGORY_IDS:
            return True

    url = (listing.url or "").lower()
    if "extended_search_extended_category" in url:
        return True
    return False


def _title_matches_brand_model(
    listing: OlxListing,
    *,
    brand: str | None,
    model: str | None,
) -> bool:
    """Метчинг за всіма keyword-варіантами (latin/RU/UA), не лише canonical query."""
    from app.services.search.brand_model_keywords import (
        _haystacks_for_match,
        text_matches_brand_filter,
        text_matches_model_filter,
    )

    raw = listing.title or ""
    if not raw:
        return False
    for haystack in _haystacks_for_match(raw):
        if brand and not text_matches_brand_filter(haystack, brand, model=model or ""):
            continue
        if model and not text_matches_model_filter(haystack, model, brand=brand or ""):
            continue
        return True
    return False


def passes_olx_filters(listing: OlxListing, params: OlxSearchParams) -> bool:
    brand_hint = params.brand_label or None
    model_hint = params.model_label or None
    if params.text_query:
        if _is_non_car_listing(listing):
            return False
        if brand_hint or model_hint:
            if not _title_matches_brand_model(listing, brand=brand_hint, model=model_hint):
                return False
        # Регіон / місто для /q-brand/ (місто не в URL)
        if params.region_label:
            if not _passes_region_filter(listing, params.region_label):
                return False
        elif not _passes_city_query(listing, params.city_query):
            return False
    elif brand_hint or model_hint:
        if not _title_matches_brand_model(listing, brand=brand_hint, model=model_hint):
            return False

    if not passes_post_filters(listing, params):
        return False

    price = _listing_price_uah(listing)
    from app.services.currency import to_uah

    price_from = params.price_from
    price_to = params.price_to
    if (params.currency or "UAH").upper() == "USD":
        if price_from is not None:
            price_from = to_uah(price_from, "USD")
        if price_to is not None:
            price_to = to_uah(price_to, "USD")

    if price_from is not None and price is not None and price < price_from:
        return False
    if price_to is not None and price is not None and price > price_to:
        return False

    year = _listing_year(listing)
    if params.year_from is not None and year is not None and year < params.year_from:
        return False
    if params.year_to is not None and year is not None and year > params.year_to:
        return False

    mileage = _listing_mileage_km(listing)
    if params.mileage_from is not None and mileage is not None and mileage < params.mileage_from * 1000:
        return False
    if params.mileage_to is not None and mileage is not None and mileage > params.mileage_to * 1000:
        return False

    blob = _listing_text_blob(listing)
    if params.fuel and not _matches_keyword_filter(blob, params.fuel, FUEL_KEYWORDS):
        return False
    if params.transmission and not _matches_keyword_filter(blob, params.transmission, TRANSMISSION_KEYWORDS):
        return False

    if params.engine_from is not None or params.engine_to is not None:
        engine = _spec_number(listing.specs or {}, "об'єм", "объем", "engine", "л")
        # Пропускаємо якщо немає даних — краще показати, ніж відкинути
        if engine is not None:
            if params.engine_from is not None and engine < params.engine_from:
                return False
            if params.engine_to is not None and engine > params.engine_to:
                return False

    return True


def passes_post_filters(listing: OlxListing, params: OlxSearchParams) -> bool:
    """Пост-фільтр для полів із spec-сторінки (drivetrain, color, …).

    Якщо специфікація відсутня (None) — не відкидаємо: картка могла не пройти
    enrich або OLX не включив поле у SSR. Краще показати зайве, ніж пропустити.
    """
    specs = listing.specs or {}

    if params.drivetrain:
        drivetrain_value = " ".join(v for v in specs.values() if isinstance(v, str)).lower()
        if drivetrain_value and params.drivetrain.lower() not in drivetrain_value:
            return False

    if params.color:
        color_value = " ".join(v for v in specs.values() if isinstance(v, str)).lower()
        if color_value and params.color.lower() not in color_value:
            return False

    if params.consumption_from is not None or params.consumption_to is not None:
        consumption = _spec_number(specs, "витрат", "consumption")
        if consumption is not None:
            if params.consumption_from is not None and consumption < params.consumption_from:
                return False
            if params.consumption_to is not None and consumption > params.consumption_to:
                return False

    if params.ev_range_from is not None or params.ev_range_to is not None:
        ev_range = _spec_number(specs, "запас ходу", "range")
        if ev_range is not None:
            if params.ev_range_from is not None and ev_range < params.ev_range_from:
                return False
            if params.ev_range_to is not None and ev_range > params.ev_range_to:
                return False

    if params.battery_from is not None or params.battery_to is not None:
        battery = _spec_number(specs, "акумулятор", "battery")
        if battery is not None:
            if params.battery_from is not None and battery < params.battery_from:
                return False
            if params.battery_to is not None and battery > params.battery_to:
                return False

    if params.power_from is not None or params.power_to is not None:
        power = _spec_number(specs, "потужність", "power", "к.с")
        if power is not None:
            if params.power_from is not None and power < params.power_from:
                return False
            if params.power_to is not None and power > params.power_to:
                return False

    if params.seats_from is not None or params.seats_to is not None:
        seats = _spec_number(specs, "місць", "міс", "seat", "сидяч")
        if seats is not None:
            seats_int = int(seats)
            if params.seats_from is not None and seats_int < params.seats_from:
                return False
            if params.seats_to is not None and seats_int > params.seats_to:
                return False

    return True


def has_next_page(
    html: str,
    current_page: int,
    *,
    page_listings_count: int = 0,
    api_page_limit: int = 40,
) -> bool:
    """Чи є наступна сторінка OLX (HTML pagination або повна сторінка результатів)."""
    if page_listings_count >= max(api_page_limit - 3, 28):
        return True

    if html:
        # totalPages у __PRERENDERED_STATE__ / __NEXT_DATA__
        for pattern in (
            r'"totalPages"\s*:\s*(\d+)',
            r'"total_pages"\s*:\s*(\d+)',
            r'"pageCount"\s*:\s*(\d+)',
        ):
            match = re.search(pattern, html)
            if match:
                try:
                    total_pages = int(match.group(1))
                    if total_pages > current_page:
                        return True
                    if total_pages <= current_page:
                        return False
                except ValueError:
                    pass

    soup = BeautifulSoup(html, "html.parser") if html else None
    if soup is None:
        return False

    pagination_links = soup.select('a[href*="page="]')
    max_page_found = current_page
    for anchor in pagination_links:
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        match = re.search(r"page=(\d+)", href)
        if match:
            max_page_found = max(max_page_found, int(match.group(1)))
    return max_page_found > current_page
