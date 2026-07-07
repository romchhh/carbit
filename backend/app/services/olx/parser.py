from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlencode, urljoin

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
    condition: Optional[str] = None
    city_query: Optional[str] = None
    price_from: Optional[int] = None
    price_to: Optional[int] = None
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
    max_pages: int = 3
    fetch_details: bool = True

    def needs_post_filter(self) -> bool:
        return any(
            [
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


VIN_PATTERN = re.compile(r"\b(?=[A-HJ-NPR-Z0-9]{17}\b)(?!.*[IOQ])[A-HJ-NPR-Z0-9]{17}\b")
PLACEHOLDER_IMAGE_MARKERS = ("no_thumbnail", "/app/static/")


def is_valid_image_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    normalized = url.strip()
    if not normalized.startswith(("http://", "https://")):
        return False
    lowered = normalized.lower()
    return not any(marker in lowered for marker in PLACEHOLDER_IMAGE_MARKERS)


def build_search_url(params: OlxSearchParams, page: int = 1) -> str:
    """Будує URL лише з path-фільтрів (марка/модель/місто).

    OLX віддає порожню SSR-сторінку для search[...] query-параметрів (рік, пробіг,
    паливо тощо), тому ці фільтри застосовуємо пост-фільтром у passes_olx_filters().
    """
    path_parts = [CATEGORY_PATH.strip("/")]

    if params.brand:
        path_parts.append(params.brand.lower().strip())
        if params.model:
            path_parts.append(params.model.lower().strip())

    path = "/" + "/".join(path_parts) + "/"

    if params.city_query:
        path = path.rstrip("/") + f"/q-{params.city_query.lower().strip()}/"

    query: dict[str, str] = {}
    if page > 1:
        query["page"] = str(page)

    url = urljoin(BASE_URL, path)
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def _extract_id_from_url(url: str) -> Optional[str]:
    match = re.search(r"-ID([A-Za-z0-9]+)\.html", url)
    return match.group(1) if match else None


def _try_extract_embedded_json(html: str) -> list[dict]:
    results: list[dict] = []
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return results

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return results

    def walk(node):
        if isinstance(node, dict):
            if "id" in node and ("url" in node or "title" in node):
                results.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return results


def parse_listing_page(html: str) -> list[OlxListing]:
    listings: list[OlxListing] = []
    seen_ids: set[str] = set()

    embedded = _try_extract_embedded_json(html)
    for raw in embedded:
        listing_id = str(raw.get("id")) if raw.get("id") is not None else None
        url = raw.get("url")
        if not url or not listing_id or listing_id in seen_ids:
            continue
        if "olx.ua" not in str(url) and not str(url).startswith("/"):
            continue
        seen_ids.add(listing_id)
        listings.append(
            OlxListing(
                listing_id=listing_id,
                title=raw.get("title"),
                url=urljoin(BASE_URL, url) if str(url).startswith("/") else str(url),
                raw_params=raw if isinstance(raw, dict) else {},
            )
        )

    if listings:
        return listings

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-testid="l-card"]')
    if not cards:
        cards = soup.select('[data-cy="l-card"]')
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
        return None

    url = urljoin(BASE_URL, link_tag["href"])
    listing_id = _extract_id_from_url(url)

    is_promoted = bool(
        card.select_one('[data-testid="adCard-featured"]')
        or "promoted" in url
        or card.find(string=re.compile("TOP|Промо", re.IGNORECASE))
    )

    title_tag = (
        card.select_one('[data-testid="ad-title"]')
        or card.select_one("h4")
        or card.select_one("h6")
        or link_tag
    )
    title = title_tag.get_text(strip=True) if title_tag else None

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

    year_match = re.search(r"(19[5-9]\d|20[0-4]\d)", params_text or title or "")
    year = year_match.group(1) if year_match else None

    mileage_match = re.search(r"([\d\s]+)\s*тис\.?\s*км", params_text or "")
    mileage = (mileage_match.group(1).replace(" ", "") + " тис.км") if mileage_match else None

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
    parts = text.split(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), None


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
        if og_image and is_valid_image_url(og_image.get("content")):
            photos.append(og_image["content"])

    price_tag = soup.select_one('[data-testid="ad-price"]') or soup.select_one('[data-cy="ad-price"]')
    price_text = price_tag.get_text(strip=True) if price_tag else None
    price, currency = _split_price(price_text)

    specs: dict[str, str] = {}
    param_rows = soup.select('[data-testid="ad-parameters-container"] p, [data-testid="ad-parameter"]')
    for row in param_rows:
        text = row.get_text(" ", strip=True)
        if ":" in text:
            key, _, value = text.partition(":")
            specs[key.strip()] = value.strip()
        elif text:
            specs.setdefault("_unlabeled", []).append(text) if isinstance(
                specs.get("_unlabeled"), list
            ) else specs.update({"_unlabeled": [text]})

    vin = None
    for value in specs.values():
        if isinstance(value, str):
            match = VIN_PATTERN.search(value)
            if match:
                vin = match.group(0)
                break
    if not vin and description:
        match = VIN_PATTERN.search(description)
        if match:
            vin = match.group(0)

    return {
        "description": description,
        "photos": photos,
        "vin": vin,
        "specs": specs,
        "price": price,
        "currency": currency,
    }


def _spec_text(specs: dict, *keys: str) -> str:
    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        if any(key.lower() in spec_key.lower() for key in keys):
            return spec_value.strip()
    return ""


def apply_details_to_listing(listing: OlxListing, details: dict) -> None:
    if not details:
        return

    listing.description = details.get("description") or listing.description
    listing.vin = details.get("vin") or listing.vin
    listing.specs = {**(listing.specs or {}), **(details.get("specs") or {})}

    photos = [url for url in details.get("photos", []) if is_valid_image_url(url)]
    if photos:
        listing.photos = photos
        listing.photo_url = photos[0]

    if not listing.price and details.get("price"):
        listing.price = details.get("price")
    if not listing.currency and details.get("currency"):
        listing.currency = details.get("currency")

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
    if not listing.url:
        return False
    if params and params.needs_detail_fetch():
        return True
    if not _listing_price(listing):
        return True
    if not _listing_year(listing):
        return True
    if not is_valid_image_url(listing.photo_url) and not any(
        is_valid_image_url(url) for url in (listing.photos or [])
    ):
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
        'id="__NEXT_DATA__"',
        "/d/uk/obyavlenie/",
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
        match = re.search(r"([\d\s]+)\s*тис", str(listing.mileage))
        if match:
            return int(re.sub(r"\s", "", match.group(1)) or "0") * 1000
        digits = re.sub(r"[^\d]", "", str(listing.mileage))
        if digits:
            value = int(digits)
            return value if value > 1000 else value * 1000

    specs = listing.specs or {}
    spec_value = _spec_text(specs, "пробіг", "mileage")
    if spec_value:
        match = re.search(r"([\d\s]+)\s*тис", spec_value)
        if match:
            return int(re.sub(r"\s", "", match.group(1)) or "0") * 1000
        digits = re.sub(r"[^\d]", "", spec_value)
        if digits:
            value = int(digits)
            return value if value > 1000 else value * 1000

    blob = f"{listing.title or ''} {listing.raw_params}"
    match = re.search(r"([\d\s]+)\s*тис\.?\s*км", blob)
    if match:
        return int(re.sub(r"\s", "", match.group(1)) or "0") * 1000
    return None


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


def passes_olx_filters(listing: OlxListing, params: OlxSearchParams) -> bool:
    if not passes_post_filters(listing, params):
        return False

    price = _listing_price_uah(listing)
    if params.price_from is not None and price is not None and price < params.price_from:
        return False
    if params.price_to is not None and price is not None and price > params.price_to:
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
        if engine is None:
            return False
        if params.engine_from is not None and engine < params.engine_from:
            return False
        if params.engine_to is not None and engine > params.engine_to:
            return False

    return True


def passes_post_filters(listing: OlxListing, params: OlxSearchParams) -> bool:
    specs = listing.specs or {}

    if params.drivetrain:
        drivetrain_value = " ".join(v for v in specs.values() if isinstance(v, str)).lower()
        if params.drivetrain.lower() not in drivetrain_value:
            return False

    if params.color:
        color_value = " ".join(v for v in specs.values() if isinstance(v, str)).lower()
        if params.color.lower() not in color_value:
            return False

    if params.consumption_from is not None or params.consumption_to is not None:
        consumption = _spec_number(specs, "витрат", "consumption")
        if consumption is None:
            return False
        if params.consumption_from is not None and consumption < params.consumption_from:
            return False
        if params.consumption_to is not None and consumption > params.consumption_to:
            return False

    if params.ev_range_from is not None or params.ev_range_to is not None:
        ev_range = _spec_number(specs, "запас ходу", "range")
        if ev_range is None:
            return False
        if params.ev_range_from is not None and ev_range < params.ev_range_from:
            return False
        if params.ev_range_to is not None and ev_range > params.ev_range_to:
            return False

    if params.battery_from is not None or params.battery_to is not None:
        battery = _spec_number(specs, "акумулятор", "battery")
        if battery is None:
            return False
        if params.battery_from is not None and battery < params.battery_from:
            return False
        if params.battery_to is not None and battery > params.battery_to:
            return False

    if params.power_from is not None or params.power_to is not None:
        power = _spec_number(specs, "потужність", "power", "к.с")
        if power is None:
            return False
        if params.power_from is not None and power < params.power_from:
            return False
        if params.power_to is not None and power > params.power_to:
            return False

    return True


def has_next_page(html: str, current_page: int) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    pagination_links = soup.select('a[href*="page="]')
    max_page_found = current_page
    for anchor in pagination_links:
        match = re.search(r"page=(\d+)", anchor.get("href", ""))
        if match:
            max_page_found = max(max_page_found, int(match.group(1)))
    return max_page_found > current_page
