#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер оголошень з розділу "Легкові автомобілі" на OLX.ua.
Розширена версія: повний набір фільтрів + повні дані по кожному
оголошенню (опис, всі фото, VIN якщо доступний, техпараметри).

⚠️ ВАЖЛИВО ПЕРЕД ВИКОРИСТАННЯМ:
- Перевір https://www.olx.ua/robots.txt та Умови користування OLX перед
  продакшн-використанням.
- Скрипт заходить на КОЖНЕ оголошення окремо, щоб дістати опис/фото/VIN —
  це суттєво збільшує кількість запитів до сайту. Тримай --max-pages
  розумним і не вимикай затримки між запитами.
- HTML OLX регулярно змінюється — якщо парсинг раптом почне повертати
  порожні/биті поля, перше що робити: відкрити оголошення в браузері,
  DevTools -> звірити актуальні data-атрибути.
- ⚠️ VIN на OLX ПУБЛІЧНО ПОКАЗУЮТЬ ДУЖЕ РІДКО (це приватні дані, за
  замовчуванням приховані до контакту з продавцем). Скрипт шукає VIN
  у тексті опису/специфікацій, але в переважній більшості випадків
  це поле буде порожнім — це не баг парсера, а особливість джерела.
- Частина фільтрів у списку нижче (тип приводу, колір, витрата палива,
  запас ходу, ємність акумулятора, потужність) НЕ підтримуються офіційним
  пошуком OLX як окремі URL-параметри (це швидше поля з детальної сторінки
  оголошення, характерні для агрегаторів типу AUTO.RIA). Тому вони
  реалізовані як ПОСТ-ФІЛЬТР: скрипт спершу знаходить оголошення за
  базовими параметрами (марка/модель/ціна/рік/пробіг/паливо/КПП/об'єм),
  тоді довантажує деталі кожного і відсіює ті, що не підходять під
  розширені критерії. Це повільніше, але чесно і надійно — краще так,
  ніж підставляти вигадані ID енумів, які просто мовчки нічого не
  відфільтрують.

Приклад запуску:
    python olx_cars_parser.py \\
        --brand bmw --model 3-seriya \\
        --condition used \\
        --price-from 400000 --price-to 900000 \\
        --year-from 2018 --year-to 2024 \\
        --city "київ" \\
        --transmission automatic \\
        --drivetrain awd --color чорний \\
        --max-pages 3

Залежності:
    pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.olx.ua"
CATEGORY_PATH = "/uk/transport/legkovye-avtomobili"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

REQUEST_TIMEOUT = 15
MIN_DELAY = 1.0
MAX_DELAY = 3.0
MAX_RETRIES = 3


# --------------------------------------------------------------------------
# Параметри пошуку
# --------------------------------------------------------------------------

@dataclass
class SearchParams:
    # Базове
    brand: Optional[str] = None
    model: Optional[str] = None
    condition: Optional[str] = None       # all/used/new/damaged (див. CONDITION_MAP)
    city_query: Optional[str] = None

    # Ціна / рік / пробіг — надійні URL-фільтри OLX
    price_from: Optional[int] = None
    price_to: Optional[int] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    mileage_from: Optional[int] = None    # тис. км
    mileage_to: Optional[int] = None

    # Технічні характеристики — частково URL, частково пост-фільтр
    fuel: Optional[str] = None            # petrol/diesel/gas/electric/hybrid
    transmission: Optional[str] = None    # manual/automatic/robot/variator
    engine_from: Optional[float] = None   # об'єм двигуна, л
    engine_to: Optional[float] = None
    drivetrain: Optional[str] = None      # fwd/rwd/awd (ПОСТ-фільтр)
    color: Optional[str] = None           # довільний текст, напр. "чорний" (ПОСТ-фільтр)
    consumption_from: Optional[float] = None  # л/100км (ПОСТ-фільтр)
    consumption_to: Optional[float] = None
    ev_range_from: Optional[int] = None       # запас ходу, км (ПОСТ-фільтр, EV)
    ev_range_to: Optional[int] = None
    battery_from: Optional[float] = None      # ємність акумулятора, кВт·год (ПОСТ-фільтр)
    battery_to: Optional[float] = None
    power_from: Optional[int] = None          # потужність, к.с. (ПОСТ-фільтр)
    power_to: Optional[int] = None

    max_pages: int = 5
    fetch_details: bool = True   # заходити на кожне оголошення за описом/фото/VIN


FUEL_MAP = {
    "petrol": "1",
    "diesel": "2",
    "gas": "5",
    "electric": "6",
    "hybrid": "7",
}

# "damaged" ("Під пригон") — окрема категорія на OLX, часто це
# оголошення типу "на запчастини"/"після ДТП". Точний enum-код треба
# звірити вручну через фільтри на сайті — тут best-effort здогадка.
CONDITION_MAP = {
    "used": "2",
    "new": "1",
}

TRANSMISSION_MAP = {
    # Значення потребують ручної звірки в браузері — OLX міг перейменувати enum.
    "manual": "1",
    "automatic": "2",
    "robot": "3",
    "variator": "4",
}


# --------------------------------------------------------------------------
# Дані оголошення
# --------------------------------------------------------------------------

@dataclass
class Listing:
    listing_id: Optional[str] = None
    title: Optional[str] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    year: Optional[str] = None
    mileage: Optional[str] = None
    city: Optional[str] = None
    published: Optional[str] = None
    url: Optional[str] = None
    photo_url: Optional[str] = None      # головне фото (зі списку)
    promoted: bool = False

    # Поля, які заповнюються тільки якщо fetch_details=True
    description: Optional[str] = None
    photos: list[str] = field(default_factory=list)
    vin: Optional[str] = None
    specs: dict = field(default_factory=dict)   # усі техпараметри "як є"

    raw_params: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Побудова URL
# --------------------------------------------------------------------------

def build_search_url(params: SearchParams, page: int = 1) -> str:
    """Формує URL для сторінки видачі на основі параметрів, які OLX
    реально підтримує як query-фільтри. Параметри, для яких немає
    надійного відповідника (drivetrain/color/consumption/ev_range/
    battery/power), сюди НЕ потрапляють — вони застосовуються пізніше
    як пост-фільтр на основі даних детальної сторінки."""
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

    if params.price_from is not None:
        query["search[filter_float_price:from]"] = str(params.price_from)
    if params.price_to is not None:
        query["search[filter_float_price:to]"] = str(params.price_to)

    if params.year_from is not None:
        query["search[filter_float_year:from]"] = str(params.year_from)
    if params.year_to is not None:
        query["search[filter_float_year:to]"] = str(params.year_to)

    if params.mileage_from is not None:
        query["search[filter_float_milage:from]"] = str(params.mileage_from)
    if params.mileage_to is not None:
        query["search[filter_float_milage:to]"] = str(params.mileage_to)

    if params.engine_from is not None:
        query["search[filter_float_engine_capacity:from]"] = str(params.engine_from)
    if params.engine_to is not None:
        query["search[filter_float_engine_capacity:to]"] = str(params.engine_to)

    if params.fuel:
        fuel_value = FUEL_MAP.get(params.fuel.lower())
        if fuel_value:
            query["search[filter_enum_fuel][0]"] = fuel_value

    if params.condition and params.condition.lower() in CONDITION_MAP:
        query["search[filter_enum_state][0]"] = CONDITION_MAP[params.condition.lower()]

    if params.transmission:
        trans_value = TRANSMISSION_MAP.get(params.transmission.lower())
        if trans_value:
            query["search[filter_enum_transmission][0]"] = trans_value

    url = urljoin(BASE_URL, path)
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def fetch_page(url: str, session: requests.Session) -> Optional[str]:
    """Завантажує HTML сторінки з обробкою помилок і повторними спробами."""
    for attempt in range(1, MAX_RETRIES + 1):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            print(f"[!] Таймаут при завантаженні {url} (спроба {attempt}/{MAX_RETRIES})")
            time.sleep(2 * attempt)
            continue
        except requests.exceptions.RequestException as exc:
            print(f"[!] Помилка запиту {url}: {exc} (спроба {attempt}/{MAX_RETRIES})")
            time.sleep(2 * attempt)
            continue

        if resp.status_code == 200:
            return resp.text

        if resp.status_code in (403, 429):
            wait = 5 * attempt
            print(f"[!] Статус {resp.status_code} для {url}. Чекаю {wait}с...")
            time.sleep(wait)
            continue

        print(f"[!] Неочікуваний статус {resp.status_code} для {url}")
        return None

    print(f"[x] Не вдалося завантажити {url} після {MAX_RETRIES} спроб.")
    return None


def _extract_id_from_url(url: str) -> Optional[str]:
    match = re.search(r"-ID([A-Za-z0-9]+)\.html", url)
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# Парсинг сторінки списку
# --------------------------------------------------------------------------

def _try_extract_embedded_json(html: str) -> list[dict]:
    """Спроба знайти дані оголошень у вбудованому __NEXT_DATA__ JSON."""
    results: list[dict] = []
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            data = None
        if data:
            def walk(node):
                if isinstance(node, dict):
                    if "id" in node and ("url" in node or "title" in node):
                        results.append(node)
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for item in node:
                        walk(item)
            walk(data)
    return results


def parse_listing_page(html: str) -> list[Listing]:
    """Парсить сторінку видачі: спершу пробує вбудований JSON, потім DOM."""
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    embedded = _try_extract_embedded_json(html)
    for raw in embedded:
        listing_id = str(raw.get("id")) if raw.get("id") is not None else None
        url = raw.get("url")
        if not url or not listing_id or listing_id in seen_ids:
            continue
        if "olx.ua" not in url and not url.startswith("/"):
            continue
        seen_ids.add(listing_id)
        listings.append(
            Listing(
                listing_id=listing_id,
                title=raw.get("title"),
                url=urljoin(BASE_URL, url) if url.startswith("/") else url,
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
        cards = soup.select('a[href*="/d/uk/obyavlenie/"]')

    for card in cards:
        try:
            listing = _parse_single_card(card)
            if listing and listing.url:
                if listing.listing_id and listing.listing_id in seen_ids:
                    continue
                if listing.listing_id:
                    seen_ids.add(listing.listing_id)
                listings.append(listing)
        except Exception as exc:  # noqa: BLE001
            print(f"[!] Пропущено оголошення через помилку парсингу списку: {exc}")
            continue

    return listings


def _parse_single_card(card) -> Optional[Listing]:
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

    year_match = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", params_text or title or "")
    year = year_match.group(1) if year_match else None

    mileage_match = re.search(r"([\d\s]+)\s*тис\.?\s*км", params_text or "")
    mileage = (mileage_match.group(1).replace(" ", "") + " тис.км") if mileage_match else None

    img_tag = card.select_one("img")
    photo_url = img_tag.get("src") or img_tag.get("data-src") if img_tag else None

    return Listing(
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
    price_text = price_text.replace("\xa0", " ").strip()
    currency = None
    if "грн" in price_text:
        currency = "UAH"
    elif "$" in price_text:
        currency = "USD"
    elif "€" in price_text:
        currency = "EUR"
    price = re.sub(r"[^\d]", "", price_text.split("грн")[0]) if "грн" in price_text else re.sub(
        r"[^\d]", "", price_text
    )
    return (price or None), currency


def _split_location_date(text: Optional[str]):
    if not text:
        return None, None
    parts = text.split(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), None


# --------------------------------------------------------------------------
# Парсинг детальної сторінки оголошення (опис, фото, VIN, специфікації)
# --------------------------------------------------------------------------

VIN_PATTERN = re.compile(r"\b(?=[A-HJ-NPR-Z0-9]{17}\b)(?!.*[IOQ])[A-HJ-NPR-Z0-9]{17}\b")


def fetch_listing_details(url: str, session: requests.Session) -> dict:
    """Завантажує сторінку оголошення й повертає опис/фото/VIN/специфікації."""
    html = fetch_page(url, session)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    description_tag = soup.select_one('[data-testid="ad_description"]') or soup.select_one(
        '[data-cy="ad_description"]'
    )
    description = description_tag.get_text("\n", strip=True) if description_tag else None

    # Фото: збираємо всі img у галереї оголошення + og:image як фолбек.
    photos: list[str] = []
    gallery = soup.select('[data-testid="ad-photo"] img, [data-testid="swiper-wrapper"] img')
    for img in gallery:
        src = img.get("src") or img.get("data-src")
        if src and src not in photos:
            photos.append(src)
    if not photos:
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.get("content"):
            photos.append(og_image["content"])

    # Специфікації: таблиця/список параметрів на сторінці оголошення.
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

    # VIN — шукаємо і в специфікаціях, і у вільному тексті опису.
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
    }


# --------------------------------------------------------------------------
# Пост-фільтрація за розширеними параметрами
# --------------------------------------------------------------------------

def _spec_number(specs: dict, *keys: str) -> Optional[float]:
    """Дістає число з першого спецпараметра, що збігся по назві ключа."""
    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        if any(k.lower() in spec_key.lower() for k in keys):
            match = re.search(r"[\d]+[.,]?\d*", spec_value.replace(" ", ""))
            if match:
                return float(match.group(0).replace(",", "."))
    return None


def passes_post_filters(listing: Listing, params: SearchParams) -> bool:
    """Перевіряє поля, які не можна надійно відфільтрувати через URL OLX."""
    specs = listing.specs or {}

    if params.drivetrain:
        drivetrain_value = " ".join(
            v for v in specs.values() if isinstance(v, str)
        ).lower()
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


# --------------------------------------------------------------------------
# Допоміжне
# --------------------------------------------------------------------------

def print_listing(listing: Listing) -> None:
    print("=" * 30)
    print(json.dumps(asdict(listing), ensure_ascii=False, indent=2))
    print("=" * 30)


def has_next_page(html: str, current_page: int) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    pagination_links = soup.select('a[href*="page="]')
    max_page_found = current_page
    for a in pagination_links:
        match = re.search(r"page=(\d+)", a.get("href", ""))
        if match:
            max_page_found = max(max_page_found, int(match.group(1)))
    return max_page_found > current_page


# --------------------------------------------------------------------------
# CLI / main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Парсер оголошень авто з OLX.ua з повним набором фільтрів."
    )
    parser.add_argument("--brand", help="Марка авто, напр. bmw")
    parser.add_argument("--model", help="Модель авто, напр. 3-seriya")
    parser.add_argument(
        "--condition", choices=list(CONDITION_MAP.keys()) + ["damaged"], help="Стан авто"
    )
    parser.add_argument("--city", dest="city_query", help="Місто/регіон (текстовий пошук)")

    parser.add_argument("--price-from", type=int, dest="price_from")
    parser.add_argument("--price-to", type=int, dest="price_to")
    parser.add_argument("--year-from", type=int, dest="year_from")
    parser.add_argument("--year-to", type=int, dest="year_to")
    parser.add_argument("--mileage-from", type=int, dest="mileage_from")
    parser.add_argument("--mileage-to", type=int, dest="mileage_to")

    parser.add_argument("--fuel", choices=list(FUEL_MAP.keys()))
    parser.add_argument("--transmission", choices=list(TRANSMISSION_MAP.keys()))
    parser.add_argument("--engine-from", type=float, dest="engine_from")
    parser.add_argument("--engine-to", type=float, dest="engine_to")
    parser.add_argument("--drivetrain", choices=["fwd", "rwd", "awd"])
    parser.add_argument("--color", help="Колір (текстовий пошук по специфікаціях)")
    parser.add_argument("--consumption-from", type=float, dest="consumption_from")
    parser.add_argument("--consumption-to", type=float, dest="consumption_to")
    parser.add_argument("--ev-range-from", type=int, dest="ev_range_from")
    parser.add_argument("--ev-range-to", type=int, dest="ev_range_to")
    parser.add_argument("--battery-from", type=float, dest="battery_from")
    parser.add_argument("--battery-to", type=float, dest="battery_to")
    parser.add_argument("--power-from", type=int, dest="power_from")
    parser.add_argument("--power-to", type=int, dest="power_to")

    parser.add_argument("--max-pages", type=int, default=5, dest="max_pages")
    parser.add_argument(
        "--no-details",
        action="store_false",
        dest="fetch_details",
        help="Не заходити на кожне оголошення (швидше, але без опису/фото/VIN)",
    )
    args = parser.parse_args()

    params = SearchParams(**vars(args))

    session = requests.Session()
    total_found = 0
    total_shown = 0

    needs_post_filter = any(
        [
            params.drivetrain,
            params.color,
            params.consumption_from,
            params.consumption_to,
            params.ev_range_from,
            params.ev_range_to,
            params.battery_from,
            params.battery_to,
            params.power_from,
            params.power_to,
        ]
    )
    if needs_post_filter and not params.fetch_details:
        print(
            "[!] Розширені фільтри (привід/колір/витрата/запас ходу/акумулятор/"
            "потужність) потребують деталей оголошення — вмикаю --fetch-details примусово."
        )
        params.fetch_details = True

    for page in range(1, params.max_pages + 1):
        url = build_search_url(params, page=page)
        print(f"\n[i] Завантажую сторінку {page}: {url}")

        html = fetch_page(url, session)
        if not html:
            print("[x] Зупиняюсь: не вдалося отримати HTML.")
            break

        page_listings = parse_listing_page(html)
        if not page_listings:
            print(f"[i] На сторінці {page} оголошень не знайдено. Завершую пагінацію.")
            break

        for listing in page_listings:
            total_found += 1

            if params.fetch_details and listing.url:
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
                details = fetch_listing_details(listing.url, session)
                listing.description = details.get("description")
                listing.photos = details.get("photos", [])
                listing.vin = details.get("vin")
                listing.specs = details.get("specs", {})

            if needs_post_filter and not passes_post_filters(listing, params):
                continue

            print_listing(listing)
            total_shown += 1

        if not has_next_page(html, page):
            print("[i] Наступної сторінки немає. Завершую.")
            break

        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    print(f"\n[i] Готово. Знайдено оголошень: {total_found}, показано після фільтрів: {total_shown}")


if __name__ == "__main__":
    main()