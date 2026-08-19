"""
Парсер car-market.net — повністю переписаний на основі реальної структури сайту.

Сайт: Next.js SSR, картки авто — <a href="/auto/..."> з текстовим вмістом.
Фільтрація через query-параметри, пагінація через ?offset=N або ?page=N.

Використання:
  python car_market_parser.py                              # всі авто (1 стор.)
  python car_market_parser.py --brands 6628               # Audi (ID бренду)
  python car_market_parser.py --brand-name volkswagen     # пошук бренду по назві
  python car_market_parser.py --min-price 5000 --max-price 15000
  python car_market_parser.py --fuel diesel --transmission auto
  python car_market_parser.py --body suv --pages 3
  python car_market_parser.py --listing-type lot          # тільки "На майданчику"
  python car_market_parser.py --sold                      # включати продані
  python car_market_parser.py --output cars.json --format json
  python car_market_parser.py --diagnose                  # діагностичний режим

Параметри фільтрів (перевірені на реальному сайті):
  brands          — числовий ID бренду (напр. 6628=Audi)
  transport_type  — 1=легкові
  min_price/max_price — ціна $
  year_from/year_to   — рік
  fuels[]         — тип палива (числові коди)
  transmissions[] — коробка (числові коди)
  drives[]        — привід (числові коди)
  body_types[]    — кузов (числові коди)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ─── Константи ────────────────────────────────────────────────────────────────

BASE_URL  = "https://car-market.net"
CATALOG   = f"{BASE_URL}/catalog"
BRANDS_URL = f"{BASE_URL}/catalog"  # бренди доступні через query ?brands=ID

# Заголовки, що імітують реальний браузер (без них — 403)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Referer": BASE_URL,
    "DNT": "1",
}

# ── Реальні коди параметрів (взяті з фільтру каталогу) ──────────────────────

# Тип палива → fuels[]
FUEL_CODES: dict[str, str] = {
    "petrol":   "1",  "бензин":  "1",
    "diesel":   "2",  "дизель":  "2",
    "gas":      "3",  "газ":     "3",  # LPG / пропан-бутан+бензин
    "electric": "4",  "електро": "4",
    "hybrid":   "5",  "гібрид":  "5",
    "methane":  "6",  "метан":   "6",
}

# Коробка передач → transmissions[]
TRANS_CODES: dict[str, str] = {
    "auto":      "1",  "автомат":  "1",
    "manual":    "2",  "механіка": "2",
    "variator":  "3",  "варіатор": "3",
    "robot":     "4",  "робот":    "4",
    "tiptronic": "5",  "типтронік":"5",
}

# Привід → drives[]
DRIVE_CODES: dict[str, str] = {
    "front": "1",  "передній": "1",
    "awd":   "2",  "повний":   "2",
    "rear":  "3",  "задній":   "3",
}

# Тип кузова → body_types[]
BODY_CODES: dict[str, str] = {
    "suv":       "1",  "позашляховик": "1",
    "hatchback": "2",  "хетчбек":      "2",
    "sedan":     "3",  "седан":        "3",
    "coupe":     "4",  "купе":         "4",
    "liftback":  "5",  "ліфтбек":      "5",
    "universal": "6",  "універсал":    "6",
    "minivan":   "7",  "мінівен":      "7",
}

# Типи оголошень (бейджі з реального сайту)
LISTING_TYPES = {
    "lot":    {"На майданчику", "авторинок"},
    "bazar":  {"Базар", "базар", "онлайн"},
    "top":    {"Top", "TOP"},
    "sold":   {"Продано"},
}

# Відомі назви брендів → числові ID (з реального каталогу)
# Взяті з URL ?brands=ID при виборі бренду у фільтрі
BRAND_IDS: dict[str, str] = {
    "audi":       "6628",
    "volkswagen": "6560",
    "toyota":     "6450",
    "bmw":        "6420",
    "ford":       "6480",
    "hyundai":    "6490",
    "honda":      "6570",
    "nissan":     "6540",
    "mercedes":   "6510",
    "kia":        "6485",
    "mazda":      "6520",
    "renault":    "6545",
    "skoda":      "6555",
    "peugeot":    "6535",
    "opel":       "6530",
    "volvo":      "6580",
    "porsche":    "6538",
    "mitsubishi": "6525",
    "chevrolet":  "6440",
    "subaru":     "6555",
    "lexus":      "6500",
    "jeep":       "6495",
    "land rover": "6498",
    "suzuki":     "6558",
}


# ─── Дата-клас для авто ───────────────────────────────────────────────────────

@dataclass
class Car:
    title:        str
    year:         Optional[int]
    price_usd:    Optional[int]
    mileage_km:   Optional[int]    # числове значення пробігу
    mileage_raw:  Optional[str]    # "126 тис.км" або "280000 тис.км"
    transmission: Optional[str]
    fuel:         Optional[str]
    engine:       Optional[str]
    location:     Optional[str]
    listing_type: Optional[str]    # "На майданчику", "Базар", "Top", "Продано"
    is_sold:      bool
    is_top:       bool
    date_added:   Optional[str]    # "19 серп." тощо
    url:          str
    image_url:    Optional[str]
    car_id:       Optional[int]    # числовий ID з URL (/auto/name-YEAR-ID)
    details:      dict = field(default_factory=dict)  # деталі з сторінки /auto/...


# ─── Парсер ───────────────────────────────────────────────────────────────────

class CarMarketParser:
    """
    Парсер каталогу car-market.net.

    Сайт — Next.js SSR, повертає готовий HTML.
    Картки авто — теги <a href="/auto/..."> з усім текстом всередині.
    Структура тексту: "Марка Модель РІК ЦІНА$ ПРОБІГтис.км Коробка Паливо ОБ'ЄМ л Місто"
    """

    def __init__(self, delay: float = 1.0, verbose: bool = False):
        self.delay   = delay
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._warm_up()

    def _warm_up(self):
        """Перший запит на головну для отримання cookies."""
        try:
            r = self.session.get(BASE_URL, timeout=15)
            if self.verbose:
                print(f"[warm-up] {r.status_code}, cookies: {dict(self.session.cookies)}",
                      file=sys.stderr)
        except Exception as e:
            print(f"[warn] warm-up failed: {e}", file=sys.stderr)
        time.sleep(0.5)

    def _get(self, url: str, params: dict | None = None) -> BeautifulSoup:
        if self.verbose:
            q = "&".join(f"{k}={v}" for k, v in (params or {}).items())
            print(f"  → GET {url}{'?' + q if q else ''}", file=sys.stderr)
        try:
            resp = self.session.get(url, params=params, timeout=20)
            if self.verbose:
                print(f"  ← {resp.status_code} ({len(resp.text)} байт)", file=sys.stderr)
            resp.raise_for_status()
        except requests.HTTPError as e:
            print(f"  [!] HTTP Error: {e}", file=sys.stderr)
            raise
        time.sleep(self.delay)
        return BeautifulSoup(resp.text, "html.parser")

    # ── Парсинг однієї картки ─────────────────────────────────────────────────

    def _parse_card(self, a_tag, badges_before: list[str]) -> Optional[Car]:
        """
        Парсить один тег <a href="/auto/...">.

        Реальний текст картки (з сайту):
          "Volvo XC60 2015 18 800$ 250 тис.км Автомат Дизель 2.00 л Житомир"
          "Volkswagen ID.4 2022 22 000$ 105 тис.км Автомат Електро 67.00 кВт·г Житомир"
          "Hyundai Tucson 2006 7 300$ 235 тис.км Ручна / Механіка Бензин Житомир"
        """
        try:
            href = a_tag.get("href", "")
            if not href or "/auto/" not in href:
                return None

            url = href if href.startswith("http") else BASE_URL + href

            # ID авто з URL: /auto/brand-model-YEAR-ID
            car_id = None
            id_match = re.search(r"-(\d+)$", href)
            if id_match:
                car_id = int(id_match.group(1))

            # Зображення
            img = a_tag.find("img")
            image_url = None
            if img:
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if src:
                    image_url = src if src.startswith("http") else BASE_URL + src

            # Текст картки — беремо лише текстові вузли (без alt зображень)
            raw = a_tag.get_text(" ", strip=True)

            # Видаляємо alt тексти зображень (вони дублюють назву авто)
            # "Volvo XC60 Volvo XC60 2015 18 800$..." → прибираємо дубль
            # Рік — перший маркер де починається корисний текст
            year_match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", raw)
            if not year_match:
                return None

            year     = int(year_match.group())
            # Назва — текст до першого року
            title_raw = raw[:year_match.start()].strip()
            # Якщо назва задублювалась ("Volvo XC60 Volvo XC60") — прибираємо дубль
            title = _deduplicate_title(title_raw)

            # Решта тексту — після року
            after_year = raw[year_match.end():].strip()

            # Ціна: "18 800$" або "7 200$"
            price = None
            price_match = re.search(r"([\d\s]+)\$", after_year)
            if price_match:
                price = int(price_match.group(1).replace("\xa0", "").replace(" ", ""))
                after_year = after_year[price_match.end():].strip()

            # Пробіг: "250 тис.км" або "280000 тис.км" (іноді без пробілу)
            mileage_raw = None
            mileage_km  = None
            mil_match = re.search(r"([\d\s]+)\s*тис\.?\s*км", after_year)
            if mil_match:
                mileage_raw = mil_match.group(0).strip()
                num_str = mil_match.group(1).replace(" ", "").replace("\xa0", "")
                num = float(num_str)
                # Деякі авто вказані як "280000 тис.км" — це помилка вводу,
                # насправді 280 тис. Якщо число > 1500 — вважаємо що вже в км
                if num > 1500:
                    mileage_km = int(num)
                else:
                    mileage_km = int(num * 1000)
                after_year = after_year[mil_match.end():].strip()

            # Розбираємо решту: "Автомат Дизель 2.00 л Житомир"
            #                або "Ручна / Механіка Бензин Житомир"
            #                або "Автомат Електро 67.00 кВт·г Житомир"
            transmission, fuel, engine, location = _parse_specs(after_year)

            # Дата: шукаємо в оригінальному тексті батьківського блоку
            # (картки рендеряться з датою поруч, але не всередині <a>)
            date_added = None

            # Бейджі для цієї картки
            listing_type = None
            is_sold      = False
            is_top       = False
            for badge in badges_before:
                b = badge.strip()
                if b in ("Продано",):
                    is_sold = True
                    listing_type = "Продано"
                elif b in ("Top", "TOP"):
                    is_top = True
                elif b in ("На майданчику",):
                    listing_type = "На майданчику"
                elif b in ("Базар",):
                    listing_type = "Базар"
                elif b:
                    listing_type = b

            return Car(
                title=title,
                year=year,
                price_usd=price,
                mileage_km=mileage_km,
                mileage_raw=mileage_raw,
                transmission=transmission,
                fuel=fuel,
                engine=engine,
                location=location,
                listing_type=listing_type,
                is_sold=is_sold,
                is_top=is_top,
                date_added=date_added,
                url=url,
                image_url=image_url,
                car_id=car_id,
            )
        except Exception as e:
            if self.verbose:
                import traceback
                print(f"  [!] Помилка парсингу картки: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            return None

    # ── Завантаження сторінки ─────────────────────────────────────────────────

    def fetch_page(self, params: dict) -> tuple[list[Car], int, int]:
        """
        Завантажує одну сторінку каталогу.
        Повертає (список_авто, total_count, parsed_count).
        """
        soup = self._get(CATALOG, params=params)

        # Загальна кількість авто (для пагінації)
        total = 0
        total_match = re.search(r"Знайдено\s+([\d\s]+)\s+авто", soup.get_text())
        if total_match:
            total = int(total_match.group(1).replace(" ", ""))

        if self.verbose:
            print(f"  [total] Знайдено {total} авто за фільтром", file=sys.stderr)

        # Знаходимо всі посилання на авто
        # Ключова особливість: бейджі (На майданчику, Базар, Top, Продано)
        # розташовані як ОКРЕМІ елементи ДО картки (не всередині <a>)
        # Обходимо всі елементи по порядку в DOM
        cars = []
        current_badges: list[str] = []
        seen_urls: set[str] = set()

        # Шукаємо в тілі сторінки послідовно
        body = soup.find("body")
        if not body:
            body = soup

        for element in body.descendants:
            if not hasattr(element, "get"):
                # Текстовий вузол — перевіряємо чи це бейдж
                text = str(element).strip()
                if text in ("На майданчику", "Базар", "Top", "TOP", "Продано", "Audi",
                            "Онлайн", "Стоянка"):
                    current_badges.append(text)
                continue

            tag_name = getattr(element, "name", None)
            if tag_name != "a":
                continue

            href = element.get("href", "")
            if "/auto/" not in href:
                continue

            url = href if href.startswith("http") else BASE_URL + href

            # На сайті часто 2 <a> з тим самим /auto/:
            # 1) порожній/клік-зона з фото, 2) текстова картка з характеристиками.
            # Якщо одразу позначити URL як seen після порожнього <a>,
            # друга (корисна) картка буде пропущена.
            raw_text = element.get_text(" ", strip=True)
            if not raw_text:
                continue

            if url in seen_urls:
                continue

            car = self._parse_card(element, list(current_badges))
            if car:
                # Дата — шукаємо наступний текстовий вузол після <a>
                date_added = _find_date_near(element)
                car.date_added = date_added
                cars.append(car)
                seen_urls.add(url)

            # Скидаємо бейджі після картки
            current_badges = []

        return cars, total, len(cars)

    # ── Деталі з сторінки авто ───────────────────────────────────────────────

    def _fetch_car_details(self, car: Car) -> dict:
        """
        Завантажує сторінку авто і витягує додаткові дані:
        - title/description/og:image
        - всі image URLs з /uploads/cars/
        - телефони (якщо присутні в HTML)
        - коротко розпарсені поля з description
        """
        try:
            soup = self._get(car.url)
        except Exception as e:
            if self.verbose:
                print(f"  [warn] detail fail for {car.url}: {e}", file=sys.stderr)
            return {}

        details: dict = {}

        # Meta
        details["page_title"] = (soup.title.get_text(strip=True) if soup.title else None)
        details["meta_description"] = _meta_content(soup, "description")
        details["og_title"] = _meta_content(soup, "og:title", prop=True)
        details["og_description"] = _meta_content(soup, "og:description", prop=True)
        details["og_image"] = _meta_content(soup, "og:image", prop=True)
        details["canonical_url"] = _meta_content(soup, "og:url", prop=True) or car.url

        # Усі картинки авто (зазвичай /uploads/cars/{id}/...)
        images: list[str] = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue
            full = src if src.startswith("http") else BASE_URL + src
            if "/uploads/cars/" in full and full not in images:
                images.append(full)
        details["images"] = images
        details["images_count"] = len(images)

        # Якщо в списку не було картинки — беремо першу з detail
        if not car.image_url and images:
            car.image_url = images[0]

        # Телефони (можуть бути в SSR, а можуть підвантажуватись кнопкою)
        phones = sorted(set(re.findall(r"\+?380\d{9}", soup.get_text(" ", strip=True))))
        details["phones"] = phones

        # Додаткові поля з meta description
        md = details.get("meta_description") or ""
        parsed = _parse_meta_description(md)
        if parsed:
            details["parsed_from_meta"] = parsed

        # Додаємо технічні маркери
        details["fetched_at_unix"] = int(time.time())
        details["source_url_path"] = urlparse(car.url).path

        return details

    def enrich_with_details(self, cars: list[Car]) -> None:
        """Підтягує деталі для кожної машини (in-place)."""
        if not cars:
            return
        print(f"  Завантаження деталей по авто: {len(cars)} шт...", file=sys.stderr)
        for i, car in enumerate(cars, 1):
            car.details = self._fetch_car_details(car)
            if i % 10 == 0 or i == len(cars):
                print(f"    деталі: {i}/{len(cars)}", file=sys.stderr)

    # ── Пошук ─────────────────────────────────────────────────────────────────

    def search(
        self,
        brands:        str | None = None,   # числовий ID або назва бренду
        min_price:     int | None = None,
        max_price:     int | None = None,
        year_from:     int | None = None,
        year_to:       int | None = None,
        fuel:          str | None = None,   # petrol/diesel/electric/hybrid/gas
        transmission:  str | None = None,   # auto/manual/variator/robot/tiptronic
        drive:         str | None = None,   # front/awd/rear
        body:          str | None = None,   # suv/sedan/hatchback/universal/minivan/coupe/liftback
        listing_type:  str | None = None,   # lot/bazar/all
        transport_type:str | None = None,   # 1=легкові
        pages:         int        = 1,
        skip_sold:     bool       = True,
        offset_step:   int        = 20,     # авто на сторінку
    ) -> list[Car]:
        """
        Пошук авто. Повертає список Car.

        brands       — числовий ID бренду (напр. "6628") або назва ("audi")
        fuel         — petrol | diesel | electric | hybrid | gas | methane
        transmission — auto | manual | variator | robot | tiptronic
        drive        — front | awd | rear
        body         — suv | sedan | hatchback | universal | minivan | coupe | liftback
        listing_type — lot (На майданчику) | bazar (Базар) | all
        pages        — кількість сторінок (1 сторінка ≈ 20 авто)
        skip_sold    — пропускати продані (True за замовч.)
        """
        params: dict[str, str] = {}

        # Бренд
        if brands:
            bid = _resolve_brand(brands)
            if bid:
                params["brands"] = bid
            else:
                print(f"[warn] Бренд '{brands}' не знайдено, ігноруємо.", file=sys.stderr)

        # Тип транспорту
        if transport_type:
            params["transport_type"] = transport_type

        # Ціна
        if min_price is not None:
            params["min_price"] = str(min_price)
        if max_price is not None:
            params["max_price"] = str(max_price)

        # Рік
        if year_from:
            params["year_from"] = str(year_from)
        if year_to:
            params["year_to"] = str(year_to)

        # Паливо (множинний вибір — fuels[])
        if fuel:
            code = FUEL_CODES.get(fuel.lower())
            if code:
                params["fuels[]"] = code
            else:
                print(f"[warn] Паливо '{fuel}' не розпізнано.", file=sys.stderr)

        # Коробка
        if transmission:
            code = TRANS_CODES.get(transmission.lower())
            if code:
                params["transmissions[]"] = code
            else:
                print(f"[warn] Коробка '{transmission}' не розпізнана.", file=sys.stderr)

        # Привід
        if drive:
            code = DRIVE_CODES.get(drive.lower())
            if code:
                params["drives[]"] = code

        # Кузов
        if body:
            code = BODY_CODES.get(body.lower())
            if code:
                params["body_types[]"] = code

        # Тип оголошення
        if listing_type and listing_type != "all":
            lt_map = {"lot": "lot", "bazar": "bazar", "online": "online"}
            lt = lt_map.get(listing_type.lower())
            if lt:
                params["listing_type"] = lt

        all_cars: list[Car] = []

        for page_num in range(1, pages + 1):
            if page_num > 1:
                params["page"] = str(page_num)
            elif "page" in params:
                del params["page"]

            print(f"  Завантаження сторінки {page_num}...", file=sys.stderr)
            try:
                cars, total, found = self.fetch_page(dict(params))
            except Exception as e:
                print(f"  [!] Помилка: {e}", file=sys.stderr)
                break

            if skip_sold:
                before = len(cars)
                cars = [c for c in cars if not c.is_sold]
                if before != len(cars) and self.verbose:
                    print(f"  [info] Пропущено {before - len(cars)} проданих авто",
                          file=sys.stderr)

            all_cars.extend(cars)
            print(f"  Знайдено {found} авто на сторінці {page_num} "
                  f"(всього за фільтром: {total})", file=sys.stderr)

            # Якщо авто на цій сторінці менше ніж очікувано — більше немає
            if found == 0 or (total > 0 and len(all_cars) >= total):
                break

        return all_cars

    # ── Діагностика ───────────────────────────────────────────────────────────

    def diagnose(self):
        """Перевіряє сайт і виводить діагностику."""
        print("\n═══ ДІАГНОСТИКА car-market.net ═══\n")

        # Крок 1: доступність
        print("1. Перевірка доступності...")
        try:
            r = self.session.get(BASE_URL, timeout=10)
            print(f"   Статус: {r.status_code}")
            print(f"   Довжина відповіді: {len(r.text)} байт")
            print(f"   Заголовок: {'OK' if r.status_code == 200 else 'ПОМИЛКА'}")
        except Exception as e:
            print(f"   ПОМИЛКА: {e}")
            return

        # Крок 2: каталог
        print("\n2. Перевірка каталогу...")
        try:
            soup = self._get(CATALOG)
            text = soup.get_text(" ", strip=True)

            # Кількість авто
            m = re.search(r"Знайдено\s+([\d\s]+)\s+авто", text)
            total = int(m.group(1).replace(" ", "")) if m else 0
            print(f"   Всього авто в каталозі: {total}")

            # Перші 3 посилання на авто
            links = [a["href"] for a in soup.find_all("a", href=True)
                     if "/auto/" in a.get("href", "")]
            print(f"   Знайдено посилань /auto/: {len(links)}")
            for l in links[:3]:
                print(f"     {l}")

            # Тест парсингу
            cars, total2, found = self.fetch_page({})
            print(f"\n3. Тест парсингу 1 сторінки:")
            print(f"   Розпізнано авто: {found}")
            if cars:
                c = cars[0]
                print(f"   Перше авто: {c.title} {c.year} ${c.price_usd}")
                print(f"   Паливо: {c.fuel}, Коробка: {c.transmission}")
                print(f"   Пробіг: {c.mileage_raw} ({c.mileage_km} км)")
                print(f"   Місто: {c.location}")
                print(f"   Тип: {c.listing_type}, Top: {c.is_top}")
                print(f"   URL: {c.url}")
                print(f"   Фото: {c.image_url}")

        except Exception as e:
            import traceback
            print(f"   ПОМИЛКА: {e}")
            traceback.print_exc()

        print("\n═══════════════════════════════════\n")


# ─── Допоміжні функції ────────────────────────────────────────────────────────

def _resolve_brand(brand: str) -> Optional[str]:
    """Перетворює назву бренду на числовий ID або повертає як є якщо вже число."""
    if brand.isdigit():
        return brand
    return BRAND_IDS.get(brand.lower())


def _deduplicate_title(title: str) -> str:
    """
    Прибирає дублювання назви: "Volvo XC60 Volvo XC60" → "Volvo XC60".
    Виникає коли alt зображення дублює текст.
    """
    words = title.split()
    half = len(words) // 2
    if half > 0 and words[:half] == words[half:]:
        return " ".join(words[:half])
    # Перевірка через регекс: "Name Name" де Name може мати 2-5 слів
    for n in range(2, min(6, len(words))):
        prefix = " ".join(words[:n])
        rest   = title[len(prefix):].strip()
        if rest.startswith(prefix):
            return prefix
    return title


def _parse_specs(text: str) -> tuple[
    Optional[str], Optional[str], Optional[str], Optional[str]
]:
    """
    Розбирає частину тексту після пробігу:
      "Автомат Дизель 2.00 л Житомир"
      "Ручна / Механіка Бензин Житомир"
      "Автомат Електро 67.00 кВт·г Житомир"
      "Ручна / Механіка Бензин 2.00 л Козятин"

    Повертає (transmission, fuel, engine, location).
    """
    text = text.strip()

    transmission = None
    fuel         = None
    engine       = None
    location     = None

    # Відомі варіанти коробки передач (точний порядок важливий)
    trans_patterns = [
        r"Ручна\s*/\s*Механіка",
        r"Автомат",
        r"Варіатор",
        r"Робот",
        r"Типтронік",
    ]

    # Відомі варіанти палива
    fuel_patterns = [
        r"Газ\s+пропан-бутан\s*/\s*Бензин",
        r"Газ\s+метан\s*/\s*Бензин",
        r"Гібрид\s+\(HEV\)",
        r"Електро",
        r"Дизель",
        r"Бензин",
        r"Газ",
    ]

    # Об'єм двигуна: "2.00 л" або "67.00 кВт·г"
    engine_pattern = r"(\d+\.\d+)\s*(л|кВт·г)"

    remaining = text

    # 1. Коробка
    for pat in trans_patterns:
        m = re.search(pat, remaining, re.IGNORECASE)
        if m:
            transmission = m.group(0).strip()
            remaining = remaining[:m.start()] + remaining[m.end():]
            remaining = remaining.strip()
            break

    # 2. Паливо
    for pat in fuel_patterns:
        m = re.search(pat, remaining, re.IGNORECASE)
        if m:
            fuel = m.group(0).strip()
            remaining = remaining[:m.start()] + remaining[m.end():]
            remaining = remaining.strip()
            break

    # 3. Двигун
    m = re.search(engine_pattern, remaining)
    if m:
        engine = m.group(0).strip()
        remaining = remaining[:m.start()] + remaining[m.end():]
        remaining = remaining.strip()

    # 4. Місто — що залишилось (очищуємо від пробілів і цифр-дат)
    remaining = re.sub(r"\s+", " ", remaining).strip()
    # Прибираємо числові залишки (дати типу "19", "17 серп.")
    remaining = re.sub(r"^\d+$", "", remaining).strip()
    if remaining and len(remaining) > 1:
        location = remaining

    return transmission, fuel, engine, location


def _find_date_near(a_tag) -> Optional[str]:
    """Шукає дату поруч з карткою авто (в сусідніх текстових вузлах)."""
    date_re = re.compile(
        r"\b\d{1,2}\s+"
        r"(?:серп|лип|черв|трав|квіт|бер|лют|січ|жовт|вер|лист|груд|черв)"
        r"\.?\b",
        re.IGNORECASE
    )
    # Шукаємо в наступних сусідах
    node = a_tag.next_sibling
    checks = 0
    while node and checks < 10:
        if hasattr(node, "get_text"):
            txt = node.get_text(" ", strip=True)
        else:
            txt = str(node).strip()
        m = date_re.search(txt)
        if m:
            return m.group(0)
        node = getattr(node, "next_sibling", None)
        checks += 1
    return None


def _meta_content(soup: BeautifulSoup, key: str, prop: bool = False) -> Optional[str]:
    if prop:
        tag = soup.find("meta", attrs={"property": key})
    else:
        tag = soup.find("meta", attrs={"name": key})
    if not tag:
        return None
    return tag.get("content")


def _parse_meta_description(text: str) -> dict:
    """
    Парсить типову description сторінки авто:
    "Купити Volvo XC60 2015 року в м. Житомир. Пробіг: 250 тис. км. Ціна: $18,800..."
    """
    out: dict = {}
    if not text:
        return out
    y = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", text)
    if y:
        out["year"] = int(y.group(1))
    city = re.search(r"в\s+м\.\s*([^\.]+)\.", text)
    if city:
        out["city"] = city.group(1).strip()
    mil = re.search(r"Пробіг:\s*([^\.]+)\.", text, re.IGNORECASE)
    if mil:
        out["mileage_text"] = mil.group(1).strip()
    price = re.search(r"Ціна:\s*\$([\d, ]+)", text, re.IGNORECASE)
    if price:
        out["price_usd_text"] = price.group(1).strip()
    return out


# ─── Вивід результатів ────────────────────────────────────────────────────────

def print_table(cars: list[Car], show_sold: bool = False):
    """Виводить результати у вигляді таблиці."""
    to_show = cars if show_sold else [c for c in cars if not c.is_sold]
    if not to_show:
        print("Авто не знайдено.")
        return

    W = 100
    print(f"\n{'═' * W}")
    print(f"  Знайдено авто: {len(to_show)}"
          + (f" (продані приховані)" if not show_sold and any(c.is_sold for c in cars) else ""))
    print(f"{'═' * W}")

    fmt = "{:<5} {:<32} {:>5} {:>10} {:>15} {:<22} {:<15} {:<12} {}"
    print(fmt.format(
        "Top", "Назва", "Рік", "Ціна $", "Пробіг",
        "Коробка", "Паливо", "Місто", "Дата"
    ))
    print("─" * W)

    for c in to_show:
        top_mark = "⭐ Top" if c.is_top else ""
        price_str = f"${c.price_usd:,}" if c.price_usd else "-"
        mileage_str = f"{c.mileage_km // 1000} тис.км" if c.mileage_km else (c.mileage_raw or "-")
        title_str = f"{c.title or '-'}"[:31]
        print(fmt.format(
            top_mark,
            title_str,
            c.year or "-",
            price_str,
            mileage_str,
            (c.transmission or "-")[:21],
            (c.fuel or "-")[:14],
            (c.location or "-")[:11],
            c.date_added or "-",
        ))

    print(f"{'═' * W}\n")

    # Статистика
    prices = [c.price_usd for c in to_show if c.price_usd]
    if prices:
        print(f"  Ціна: мін ${min(prices):,}  |  макс ${max(prices):,}  "
              f"|  середня ${sum(prices) // len(prices):,}")

    mileages = [c.mileage_km for c in to_show if c.mileage_km]
    if mileages:
        print(f"  Пробіг: мін {min(mileages) // 1000} тис.  |  "
              f"макс {max(mileages) // 1000} тис.  |  "
              f"середній {sum(mileages) // len(mileages) // 1000} тис. км")
    print()


def print_json_output(cars: list[Car], output_file: Optional[str] = None):
    """Виводить JSON або зберігає у файл."""
    data = json.dumps(
        [asdict(c) for c in cars],
        ensure_ascii=False, indent=2
    )
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"✓ Збережено {len(cars)} авто у {output_file}")
    else:
        print(data)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Парсер авторинку car-market.net",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    g = p.add_argument_group("Фільтри")
    g.add_argument("--brands", "-b",
                   help="ID або назва бренду (audi, volkswagen, toyota...)")
    g.add_argument("--min-price", type=int, metavar="$",
                   help="Мінімальна ціна, $")
    g.add_argument("--max-price", type=int, metavar="$",
                   help="Максимальна ціна, $")
    g.add_argument("--year-from", type=int, help="Рік від")
    g.add_argument("--year-to",   type=int, help="Рік до")
    g.add_argument("--fuel", "-f",
                   choices=["petrol", "diesel", "electric", "hybrid", "gas", "methane"],
                   help="Тип палива")
    g.add_argument("--transmission", "-t",
                   choices=["auto", "manual", "variator", "robot", "tiptronic"],
                   help="Коробка передач")
    g.add_argument("--drive",
                   choices=["front", "awd", "rear"],
                   help="Привід")
    g.add_argument("--body",
                   choices=["suv", "sedan", "hatchback", "universal",
                            "minivan", "coupe", "liftback"],
                   help="Тип кузова")
    g.add_argument("--listing-type",
                   choices=["all", "lot", "bazar"],
                   default="all",
                   help="Тип оголошення: all=всі, lot=На майданчику, bazar=Базар")
    g.add_argument("--cars", dest="transport_type",
                   action="store_const", const="1",
                   help="Тільки легкові (transport_type=1)")

    p.add_argument("--pages",    type=int, default=1,  help="Кількість сторінок (за замовч. 1)")
    p.add_argument("--sold",     action="store_true",  help="Включати продані авто")
    p.add_argument("--output", "-o", metavar="FILE",   help="Зберегти у JSON-файл")
    p.add_argument("--format", choices=["table", "json"], default="table",
                   help="Формат виводу")
    p.add_argument("--delay",  type=float, default=1.0, help="Затримка між запитами, сек")
    p.add_argument("--verbose", "-v", action="store_true", help="Детальний лог")
    p.add_argument("--diagnose", action="store_true",  help="Діагностичний режим")
    return p


def main():
    cli   = build_cli()
    args  = cli.parse_args()

    parser = CarMarketParser(delay=args.delay, verbose=args.verbose)

    if args.diagnose:
        parser.diagnose()
        return

    print("🔍 Пошук авто на car-market.net...", file=sys.stderr)

    cars = parser.search(
        brands        = args.brands,
        min_price     = args.min_price,
        max_price     = args.max_price,
        year_from     = args.year_from,
        year_to       = args.year_to,
        fuel          = args.fuel,
        transmission  = args.transmission,
        drive         = args.drive,
        body          = args.body,
        listing_type  = args.listing_type,
        transport_type= args.transport_type,
        pages         = args.pages,
        skip_sold     = not args.sold,
    )

    # Завжди підтягуємо detail-дані і зберігаємо JSON
    parser.enrich_with_details(cars)

    output_file = args.output or f"cars_{int(time.time())}.json"
    print_json_output(cars, output_file)

    if args.format == "json":
        # Якщо явно просили JSON, не дублюємо всю таблицю
        print(f"JSON output: {output_file}")
    else:
        print_table(cars, show_sold=args.sold)
        print(f"JSON output: {output_file}")


if __name__ == "__main__":
    main()