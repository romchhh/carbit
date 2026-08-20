"""
Парсер reono.ua — на основі реальної структури сайту.

Сайт: SSR HTML, картки авто — <a href="/brand-model-ID">.
Фільтрація через СЕГМЕНТИ URL (не query-параметри!):
  /legkovoe-avto/{регіон}/{місто}/{бренд}/{модель}
Пагінація — теж сегмент шляху: /legkovoe-avto/{фільтр}/page={N}

Використання:
  python reono_parser.py                                   # всі авто (1 стор. ≈ 20-30 шт.)
  python reono_parser.py --brand opel --model vectra
  python reono_parser.py --region kharkiv --brand volkswagen
  python reono_parser.py --region kyiv --city --pages 3
  python reono_parser.py --sort price_asc --pages 2
  python reono_parser.py --output cars.json --format json
  python reono_parser.py --diagnose

Примітка: reono.ua не має прямої фільтрації за ціною/роком через URL —
вона робиться через форму (можливо AJAX/POST), тому в цьому парсері
фільтр за ціною/роком застосовується ПІСЛЯ завантаження (client-side).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# ─── Константи ────────────────────────────────────────────────────────────────

BASE_URL = "https://reono.ua"
CATALOG_PATH = "legkovoe-avto"   # легкові авто

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Referer": BASE_URL,
    "DNT": "1",
}

# Сортування: параметри з реального сайту (значення в select — треба уточнювати,
# тут використовуємо query fallback ?sort=..., якщо сайт це підтримує)
SORT_MAP = {
    "relevance":   None,          # За замовчуванням (Актуальністю)
    "date":        "date",        # Датою публікації
    "year_desc":   "year_desc",   # Роком випуску: новіші
    "year_asc":    "year_asc",    # Роком випуску: старіші
    "price_desc":  "price_desc",  # Ціною: від дорожчих
    "price_asc":   "price_asc",   # Ціною: від дешевших
    "mileage":     "mileage",     # Пробігом
}

# Регіони — транслітерація як на сайті (спостережена з реальних URL)
REGION_SLUGS: dict[str, str] = {
    "kharkiv":      "xarkovskaya-oblast",
    "kharkivska":   "xarkovskaya-oblast",
    "kyiv":         "kievskaya-oblast",
    "kyivska":      "kievskaya-oblast",
    "chernivtsi":   "chernovickaya-oblast",
    "chernivetska": "chernovickaya-oblast",
    "poltava":      "poltavskaya-oblast",
    "poltavska":    "poltavskaya-oblast",
    "ternopil":     "ternopolskaya-oblast",
    "ternopilska":  "ternopolskaya-oblast",
    "dnipro":       "dnepropetrovskaya-oblast",
    "dnipropetrovska": "dnepropetrovskaya-oblast",
    "kherson":      "xersonskaya-oblast",
    "khersonska":   "xersonskaya-oblast",
    "ivano-frankivsk": "ivano-frankovskaya-oblast",
    "crimea":       "krym-avtonomnaya-respublika",
    # Додаткові — типова російськомовна транслітерація на цьому сайті,
    # НЕ перевірені живим запитом, використовуйте на власний розсуд:
    "lviv":         "lvovskaya-oblast",
    "odesa":        "odesskaya-oblast",
    "vinnytsia":    "vinnickaya-oblast",
    "zhytomyr":     "zhitomirskaya-oblast",
    "zaporizhzhia": "zaporozhskaya-oblast",
    "sumy":         "sumskaya-oblast",
    "cherkasy":     "cherkasskaya-oblast",
    "chernihiv":    "chernigovskaya-oblast",
    "rivne":        "rovenskaya-oblast",
    "volyn":        "volynskaya-oblast",
    "zakarpattia":  "zakarpatskaya-oblast",
    "mykolaiv":     "nikolaevskaya-oblast",
}

FUEL_WORDS = {"бензин", "дизель", "газ", "гібрид", "електро", "метан"}
TRANS_WORDS = {"автомат", "механіка", "варіатор", "робот", "типтронік"}


# ─── Дата-клас ────────────────────────────────────────────────────────────────

@dataclass
class Car:
    title:        str
    brand:        Optional[str]
    model:        Optional[str]
    year:         Optional[int]
    price_usd:    Optional[int]
    price_uah:    Optional[int]
    mileage_km:   Optional[int]
    is_new:       bool             # "Нове авто" — пробіг відсутній
    transmission: Optional[str]
    fuel:         Optional[str]
    engine:       Optional[str]    # "1.8" або "24 кВт·г"
    location:     Optional[str]
    is_premium:   bool             # бейдж "Преміум"
    url:          str
    image_url:    Optional[str]
    car_id:       Optional[int]


# ─── Парсер ───────────────────────────────────────────────────────────────────

class ReonoParser:
    """
    Парсер каталогу reono.ua.

    Фільтри — сегменти URL: /legkovoe-avto/{регіон}/{місто}/{бренд}/{модель}
    Пагінація — сегмент шляху: {filter_path}/page={N}
    """

    def __init__(self, delay: float = 1.0, verbose: bool = False):
        self.delay   = delay
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._warm_up()

    def _warm_up(self):
        try:
            r = self.session.get(BASE_URL, timeout=15)
            if self.verbose:
                print(f"[warm-up] {r.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"[warn] warm-up failed: {e}", file=sys.stderr)
        time.sleep(0.5)

    def _get(self, url: str) -> BeautifulSoup:
        if self.verbose:
            print(f"  → GET {url}", file=sys.stderr)
        resp = self.session.get(url, timeout=20)
        if self.verbose:
            print(f"  ← {resp.status_code} ({len(resp.text)} байт)", file=sys.stderr)
        resp.raise_for_status()
        time.sleep(self.delay)
        return BeautifulSoup(resp.text, "html.parser")

    # ── Побудова URL фільтра ────────────────────────────────────────────────

    @staticmethod
    def build_path(
        region: str | None = None,
        city:   str | None = None,
        brand:  str | None = None,
        model:  str | None = None,
    ) -> str:
        """Будує шлях фільтра: legkovoe-avto/region/city/brand/model"""
        segments = [CATALOG_PATH]
        if region:
            segments.append(_resolve_region(region))
        if city:
            segments.append(_slugify(city))
        if brand:
            segments.append(_slugify(brand))
        if model:
            segments.append(_slugify(model))
        return "/".join(segments)

    # ── Парсинг однієї картки ───────────────────────────────────────────────

    def _parse_card(self, a_tag, is_premium: bool) -> Optional[Car]:
        try:
            href = a_tag.get("href", "")
            if not href or href.count("-") < 1:
                return None
            # Посилання на авто: /brand-model-ID (без інших відомих префіксів)
            path = href.lstrip("/")
            if "/" in path:
                return None  # це не картка авто (напр. навігаційне посилання)

            id_match = re.search(r"-(\d+)$", path)
            if not id_match:
                return None
            car_id = int(id_match.group(1))

            url = href if href.startswith("http") else BASE_URL + href

            img = a_tag.find("img")
            image_url = None
            if img:
                src = img.get("src") or img.get("data-src")
                if src:
                    image_url = src if src.startswith("http") else BASE_URL + src

            title_text = a_tag.get_text(" ", strip=True)
            year_match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", title_text)
            if not year_match:
                return None
            year  = int(year_match.group())
            title = title_text.strip()

            # brand/model зі slug URL: /opel-vectra-115176
            slug = re.sub(r"-\d+$", "", path)
            brand, model = _split_brand_model(slug, title, year)

            return Car(
                title=title,
                brand=brand,
                model=model,
                year=year,
                price_usd=None,
                price_uah=None,
                mileage_km=None,
                is_new=False,
                transmission=None,
                fuel=None,
                engine=None,
                location=None,
                is_premium=is_premium,
                url=url,
                image_url=image_url,
                car_id=car_id,
            )
        except Exception as e:
            if self.verbose:
                print(f"  [!] Помилка парсингу картки: {e}", file=sys.stderr)
            return None

    def fetch_page(self, path: str) -> tuple[list[Car], int]:
        """Завантажує одну сторінку. Повертає (список авто, total_count)."""
        url = f"{BASE_URL}/{path}"
        soup = self._get(url)

        page_text = soup.get_text(" ", strip=True)
        total = 0
        for pattern in (
            r"Найдено:?\s*([\d\s]+)\s*авто",
            r"Знайдено:?\s*([\d\s]+)\s*авто",
        ):
            m = re.search(pattern, page_text, re.IGNORECASE)
            if m:
                total = int(m.group(1).replace(" ", ""))
                break
        if not total:
            ads_match = re.search(r'"ads_count"\s*:\s*(\d+)', str(soup))
            if ads_match:
                total = int(ads_match.group(1))

        cars: list[Car] = []
        seen_ids: set[int] = set()
        for card in soup.select("article[data-announcement-id]"):
            car = _parse_car_card(card)
            if not car or not car.car_id or car.car_id in seen_ids:
                continue
            seen_ids.add(car.car_id)
            cars.append(car)

        if cars:
            return cars, total

        # Fallback для старої розмітки.
        body = soup.find("body") or soup
        pending_premium = False
        for element in body.descendants:
            if not hasattr(element, "get"):
                if str(element).strip() == "Преміум":
                    pending_premium = True
                continue
            if getattr(element, "name", None) != "a":
                continue
            slug = _listing_slug(element.get("href", ""))
            if not slug:
                continue
            id_match = re.search(r"-(\d+)$", slug)
            if not id_match:
                continue
            car_id = int(id_match.group(1))
            if car_id in seen_ids:
                continue
            car = self._parse_card(element, pending_premium)
            if not car:
                continue
            seen_ids.add(car_id)
            _fill_specs_from_context(element, car)
            cars.append(car)
            pending_premium = False

        return cars, total

    # ── Пошук ────────────────────────────────────────────────────────────────

    def search(
        self,
        region: str | None = None,
        city:   str | None = None,
        brand:  str | None = None,
        model:  str | None = None,
        sort:   str | None = None,
        pages:  int = 1,
        min_price: int | None = None,
        max_price: int | None = None,
        year_from: int | None = None,
        year_to:   int | None = None,
    ) -> list[Car]:
        base_path = self.build_path(region=region, city=city, brand=brand, model=model)

        all_cars: list[Car] = []
        for page_num in range(1, pages + 1):
            path = base_path if page_num == 1 else f"{base_path}/page={page_num}"

            print(f"  Завантаження сторінки {page_num}...", file=sys.stderr)
            try:
                cars, total = self.fetch_page(path)
            except requests.HTTPError as e:
                print(f"  [!] HTTP помилка: {e}", file=sys.stderr)
                break
            except Exception as e:
                print(f"  [!] Помилка: {e}", file=sys.stderr)
                break

            all_cars.extend(cars)
            print(f"  Знайдено {len(cars)} авто на сторінці {page_num} "
                  f"(всього за фільтром: {total})", file=sys.stderr)

            if len(cars) == 0 or (total and len(all_cars) >= total):
                break

        # Клієнтська фільтрація (сайт не підтримує ціну/рік через URL)
        if min_price is not None:
            all_cars = [c for c in all_cars if c.price_usd and c.price_usd >= min_price]
        if max_price is not None:
            all_cars = [c for c in all_cars if c.price_usd and c.price_usd <= max_price]
        if year_from is not None:
            all_cars = [c for c in all_cars if c.year and c.year >= year_from]
        if year_to is not None:
            all_cars = [c for c in all_cars if c.year and c.year <= year_to]

        return all_cars

    # ── Діагностика ──────────────────────────────────────────────────────────

    def diagnose(self):
        print("\n═══ ДІАГНОСТИКА reono.ua ═══\n")
        print("1. Перевірка доступності...")
        try:
            r = self.session.get(BASE_URL, timeout=10)
            print(f"   Статус: {r.status_code}, довжина: {len(r.text)} байт")
        except Exception as e:
            print(f"   ПОМИЛКА: {e}")
            return

        print("\n2. Перевірка каталогу /legkovoe-avto...")
        try:
            cars, total = self.fetch_page(CATALOG_PATH)
            print(f"   Всього авто в каталозі: {total}")
            print(f"   Розпізнано на 1 сторінці: {len(cars)}")
            if cars:
                c = cars[0]
                print(f"\n3. Перше авто:")
                print(f"   {c.title} — ${c.price_usd} / {c.price_uah}₴")
                print(f"   Пробіг: {c.mileage_km} км (нове: {c.is_new})")
                print(f"   Коробка: {c.transmission}, Паливо: {c.fuel}, Двигун: {c.engine}")
                print(f"   Місто: {c.location}, Преміум: {c.is_premium}")
                print(f"   URL: {c.url}")
        except Exception as e:
            import traceback
            print(f"   ПОМИЛКА: {e}")
            traceback.print_exc()
        print("\n═════════════════════════════\n")


# ─── Допоміжні функції ────────────────────────────────────────────────────────

def _listing_slug(href: str) -> Optional[str]:
    href = (href or "").strip()
    if not href:
        return None
    path = urlparse(href).path if href.startswith("http") else href.lstrip("/")
    path = path.strip("/")
    if not path or "/" in path or not re.search(r"-\d+$", path):
        return None
    if path.startswith(("legkovoe-avto", "gruzovoj", "info", "catalog", "profile", "announcement")):
        return None
    return path


def _parse_int(value: object) -> Optional[int]:
    if value is None:
        return None
    text = str(value).replace(" ", "").replace("\xa0", "")
    return int(text) if text.isdigit() else None


def _parse_car_card(card) -> Optional[Car]:
    car_id = _parse_int(card.get("data-announcement-id"))
    if not car_id:
        return None

    brand = (card.get("data-announcement-brand") or "").strip() or None
    model = (card.get("data-announcement-model") or "").strip() or None

    context = {}
    raw_ctx = card.get("data-analytics-context")
    if raw_ctx:
        try:
            parsed = json.loads(raw_ctx)
            if isinstance(parsed, dict):
                context = parsed
        except json.JSONDecodeError:
            pass

    title_el = card.select_one(".car-card__title")
    title = title_el.get_text(" ", strip=True) if title_el else ""
    url = ""
    if title_el and title_el.get("href"):
        href = title_el["href"]
        url = href if href.startswith("http") else BASE_URL + href
    if not url:
        link = card.select_one("a[data-announcement-link][href]")
        if link:
            href = link.get("href", "")
            url = href if href.startswith("http") else BASE_URL + href

    year = _parse_int(context.get("year_range"))
    if year is None and title:
        year_match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", title)
        if year_match:
            year = int(year_match.group())
    if not title and brand:
        title = " ".join(part for part in (brand, model, str(year or "")) if part).strip()

    price_usd = _parse_int(context.get("price_range"))
    price_uah = None
    usd_el = card.select_one("[data-price-usd]")
    uah_el = card.select_one("[data-price-uah]")
    if usd_el:
        price_usd = _parse_int(usd_el.get("data-price-usd")) or price_usd
    if uah_el:
        price_uah = _parse_int(uah_el.get("data-price-uah"))

    mileage_km = None
    mileage_val = _parse_int(context.get("mileage_range"))
    if mileage_val is not None:
        mileage_km = mileage_val * 1000 if mileage_val < 1000 else mileage_val
    else:
        for tag in card.select(".car-card__tag"):
            txt = tag.get_text(" ", strip=True)
            mil_match = re.search(r"(\d[\d\s]*)\s*км", txt)
            if mil_match:
                mileage_km = _parse_int(mil_match.group(1))
                break

    card_text = card.get_text(" ", strip=True)
    is_new = bool(re.search(r"Нове\s+авто", card_text, re.IGNORECASE))

    gearbox = str(context.get("gearbox_type") or "").lower()
    transmission = {
        "variator": "Варіатор",
        "automatic": "Автомат",
        "auto": "Автомат",
        "manual": "Механіка",
    }.get(gearbox)

    fuel_key = str(context.get("fuel_type") or "").lower()
    fuel = {
        "petrol": "Бензин",
        "diesel": "Дизель",
        "gas": "Газ",
        "hybrid": "Гібрид",
        "electric": "Електро",
    }.get(fuel_key)
    engine = None
    for tag in card.select(".car-card__tag"):
        txt = tag.get_text(" ", strip=True)
        if "км" in txt.lower():
            continue
        fuel_match = re.search(
            r"(бензин|дизель|газ|гібрид|електро)\s*,?\s*(\d+\.\d+)",
            txt,
            re.IGNORECASE,
        )
        if fuel_match:
            fuel = fuel or fuel_match.group(1).capitalize()
            engine = fuel_match.group(2)
            break

    location = (context.get("location_name") or "").strip() or None
    if not location:
        loc_el = card.select_one(".subtitle-car-card__item")
        if loc_el:
            location = loc_el.get_text(" ", strip=True) or None

    image_url = None
    for img in card.select("img[src]"):
        src = (img.get("src") or "").strip()
        if not src or "no_img" in src:
            continue
        image_url = src if src.startswith("http") else BASE_URL + src
        break

    is_premium = bool(card.find(string=re.compile(r"^\s*Преміум\s*$")))

    return Car(
        title=title,
        brand=brand,
        model=model,
        year=year,
        price_usd=price_usd,
        price_uah=price_uah,
        mileage_km=mileage_km,
        is_new=is_new,
        transmission=transmission,
        fuel=fuel,
        engine=engine,
        location=location,
        is_premium=is_premium,
        url=url,
        image_url=image_url,
        car_id=car_id,
    )


def _slugify(text: str) -> str:
    """Проста slug-конверсія для brand/model/city у latin-lower-dash формат."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def _resolve_region(region: str) -> str:
    key = region.strip().lower()
    return REGION_SLUGS.get(key, _slugify(region))


def _split_brand_model(slug: str, title: str, year: int) -> tuple[Optional[str], Optional[str]]:
    """
    Розбиває "opel-vectra" на (Opel, Vectra), звіряючи з title.
    Title зазвичай "Opel Vectra 1997" — беремо перші 1-2 слова як бренд/модель.
    """
    words = title.split(str(year))[0].strip().split()
    if len(words) >= 2:
        return words[0], " ".join(words[1:])
    elif len(words) == 1:
        return words[0], None
    return None, None


def _fill_specs_from_context(a_tag, car: Car, max_siblings: int = 25) -> None:
    """
    Проходить по сусідніх вузлах після картки, збираючи:
    ціну, пробіг, коробку, паливо, об'єм двигуна, місто.

    Реальний порядок на сайті (спостережено):
      Місто
      "XXX XXX км" АБО "Нове авто"
      [Коробка передач]  (може бути відсутня для електро)
      "Паливо, X.X" АБО "XX кВт·г" + "Електро" (окремо)
      "ЦІНА $ ЦІНА₴"
    """
    node = a_tag.next_sibling
    count = 0
    collected: list[str] = []

    while node and count < max_siblings:
        if hasattr(node, "get_text"):
            # Зупиняємось якщо натрапили на наступну картку авто
            if getattr(node, "name", None) == "a" and node.get("href", "").count("-") >= 1:
                break
            txt = node.get_text(" ", strip=True)
        else:
            txt = str(node).strip()

        if txt:
            collected.append(txt)
        node = getattr(node, "next_sibling", None)
        count += 1

        # Зупиняємось після знаходження ціни (кінець картки)
        if txt and re.search(r"\d\s*\$", txt):
            break

    full_text = " ".join(collected)

    # Ціна: "7350 $ 328549 ₴" або "700 $ 31290 ₴"
    # (?<!\.) — критично важливо: без цього regex жадібно захоплює "8" з
    # об'єму двигуна "1.8" як початок ціни (перевірено на реальних даних:
    # "Бензин, 1.8 700 $" без цього давало price_usd=8700 замість 700)
    price_match = re.search(r"(?<!\.)\b(\d[\d\s]*?)\s*\$\s*(\d[\d\s]*)\s*₴", full_text)
    if price_match:
        car.price_usd = int(price_match.group(1).replace(" ", ""))
        car.price_uah = int(price_match.group(2).replace(" ", ""))

    # Пробіг або нове авто
    if re.search(r"Нове\s+авто", full_text, re.IGNORECASE):
        car.is_new = True
    else:
        mil_match = re.search(r"(\d[\d\s]*)\s*км", full_text)
        if mil_match:
            car.mileage_km = int(mil_match.group(1).replace(" ", ""))

    # Коробка передач
    for word in TRANS_WORDS:
        m = re.search(word, full_text, re.IGNORECASE)
        if m:
            car.transmission = m.group(0).capitalize()
            break

    # Паливо + об'єм (без \S* — паливні слова фіксовані, "Бензин," з комою
    # раніше потрапляло в назву палива; тепер захоплюємо лише саме слово)
    for word in FUEL_WORDS:
        m = re.search(word, full_text, re.IGNORECASE)
        if m:
            car.fuel = m.group(0).capitalize()
            # Об'єм після коми: "Бензин, 1.8"
            engine_match = re.search(rf"{word}\S*\s*,?\s*(\d+\.\d+)", full_text, re.IGNORECASE)
            if engine_match:
                car.engine = engine_match.group(1)
            break

    # Електро — об'єм у кВт·г окремо
    kwh_match = re.search(r"(\d+)\s*кВт[·•]?г", full_text)
    if kwh_match:
        car.engine = f"{kwh_match.group(1)} кВт·г"

    # Місто — перший "чистий" текстовий рядок без цифр/спецслів
    for c in collected:
        if (c and not re.search(r"\d", c)
                and c.lower() not in FUEL_WORDS
                and c.lower() not in TRANS_WORDS
                and "км" not in c.lower()
                and c != "Преміум"):
            car.location = c
            break


# ─── Вивід ────────────────────────────────────────────────────────────────────

def print_table(cars: list[Car]):
    if not cars:
        print("Авто не знайдено.")
        return

    W = 105
    print(f"\n{'═' * W}")
    print(f"  Знайдено авто: {len(cars)}")
    print(f"{'═' * W}")
    fmt = "{:<4} {:<30} {:>5} {:>9} {:>12} {:<14} {:<16} {:<14}"
    print(fmt.format("★", "Назва", "Рік", "Ціна $", "Пробіг", "Коробка", "Паливо", "Місто"))
    print("─" * W)

    for c in cars:
        star = "★" if c.is_premium else ""
        price = f"${c.price_usd:,}" if c.price_usd else "-"
        mileage = "Нове" if c.is_new else (f"{c.mileage_km:,} км" if c.mileage_km else "-")
        fuel = c.fuel or "-"
        if c.engine:
            fuel += f" {c.engine}"
        print(fmt.format(
            star,
            (c.title or "-")[:29],
            c.year or "-",
            price,
            mileage,
            (c.transmission or "-")[:13],
            fuel[:15],
            (c.location or "-")[:13],
        ))
    print(f"{'═' * W}\n")

    prices = [c.price_usd for c in cars if c.price_usd]
    if prices:
        print(f"  Ціна: мін ${min(prices):,}  |  макс ${max(prices):,}  |  "
              f"середня ${sum(prices)//len(prices):,}")
    print()


def print_json_output(cars: list[Car], output_file: Optional[str] = None):
    data = json.dumps([asdict(c) for c in cars], ensure_ascii=False, indent=2)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"✓ Збережено {len(cars)} авто у {output_file}")
    else:
        print(data)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Парсер авторинку reono.ua",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--region", help="Регіон (напр. kharkiv, kyiv, chernivtsi...)")
    p.add_argument("--city",   help="Місто (латиницею або кирилицею)")
    p.add_argument("--brand",  help="Марка (напр. opel, volkswagen)")
    p.add_argument("--model",  help="Модель (напр. vectra, golf)")
    p.add_argument("--sort",   choices=list(SORT_MAP.keys()), default="relevance",
                    help="Сортування")
    p.add_argument("--pages",  type=int, default=1, help="Кількість сторінок")
    p.add_argument("--min-price", type=int, help="Мін. ціна $ (клієнтський фільтр)")
    p.add_argument("--max-price", type=int, help="Макс. ціна $ (клієнтський фільтр)")
    p.add_argument("--year-from", type=int, help="Рік від (клієнтський фільтр)")
    p.add_argument("--year-to",   type=int, help="Рік до (клієнтський фільтр)")
    p.add_argument("--output", "-o", help="Зберегти у JSON-файл")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.add_argument("--delay",  type=float, default=1.0)
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--diagnose", action="store_true")
    return p


def main():
    cli  = build_cli()
    args = cli.parse_args()

    parser = ReonoParser(delay=args.delay, verbose=args.verbose)

    if args.diagnose:
        parser.diagnose()
        return

    print("🔍 Пошук авто на reono.ua...", file=sys.stderr)

    cars = parser.search(
        region=args.region,
        city=args.city,
        brand=args.brand,
        model=args.model,
        sort=args.sort,
        pages=args.pages,
        min_price=args.min_price,
        max_price=args.max_price,
        year_from=args.year_from,
        year_to=args.year_to,
    )

    if args.format == "json" or args.output:
        print_json_output(cars, args.output)
        if args.output and args.format == "table":
            print_table(cars)
    else:
        print_table(cars)


if __name__ == "__main__":
    main()