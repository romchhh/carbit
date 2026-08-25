"""
Парсер rst.ua (m.rst.ua) — на основі аналізу реальної структури сайту.

⚠ ВАЖЛИВА ВІДМІННІСТЬ від car_market_parser.py та reono_parser.py:
rst.ua має АГРЕСИВНІШИЙ бот-захист — навіть інструмент web_fetch не зміг
напряму отримати сторінку (на відміну від двох попередніх сайтів). Структура
парсингу нижче побудована на основі РЕАЛЬНИХ фрагментів тексту карток, знайдених
через пошук (Google-кеш/сніпети), а НЕ на прямому огляді живого HTML.
Регекс-логіка розбору протестована на цих реальних зразках і працює коректно,
але точна структура DOM (класи/теги) — це обґрунтоване припущення.

Якщо звичайні requests-заголовки не проходять (ймовірно, Cloudflare або
подібний захист) — спробуйте встановити `cloudscraper` замість `requests`:
    pip install cloudscraper --break-system-packages
і замінити requests.Session() на cloudscraper.create_scraper() у __init__.

Підтверджена URL-схема (сегменти шляху, як і reono.ua):
  /ukr/oldcars/{місто}/                       — всі авто в місті
  /ukr/oldcars/{бренд}/                       — бренд по всій Україні
  /ukr/oldcars/{бренд}/{модель}/              — бренд+модель по Україні
  /ukr/oldcars/{місто}/{бренд}/               — бренд у місті
  /ukr/oldcars/{місто}/{бренд}/{модель}/      — бренд+модель у місті

Індивідуальне оголошення: /ukr/oldcars/{бренд}/{модель}/{бренд}_{модель}_{ID}.html

Реальний текст картки (два спостережені варіанти форматування):
  "OPEL Vectra•C · $6'500= 282'600 грн · 2007(325 тис) 2.8 Бенз(Авт) Київ · сьогодні, ТОП"
  "AUDI A4 · $13'700= 615'900 грн · 2015 р (226 тис) 2.0 Бенз (Авт) 226'000 km · Київська · 1 тиждень"

Використання:
  python rst_parser.py --city kiev
  python rst_parser.py --brand opel --model vectra
  python rst_parser.py --city kiev --brand opel --pages 2
  python rst_parser.py --output cars.json --format json
  python rst_parser.py --diagnose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup


# ─── Константи ────────────────────────────────────────────────────────────────

RST_BASE_URL = "https://m.rst.ua"
CATALOG_PATH = "ukr/oldcars"

RST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Referer": RST_BASE_URL,
    "DNT": "1",
}

# Скорочення палива, як вони зустрічаються в текстах карток
FUEL_ABBR = {
    "Диз":     "Дизель",
    "Бенз":    "Бензин",
    "Г/Б":     "Газ/Бензин",
    "Газ":     "Газ",
    "Гібр":    "Гібрид",
    "Електро": "Електро",
}

TRANS_ABBR = {
    "Авт": "Автомат",
    "Мех": "Механіка",
    "Роб": "Робот",
    "Вар": "Варіатор",
}

# Мітки стану/умов угоди, що трапляються в картках
KNOWN_TAGS = (
    "хороша ціна", "підозріло низька", "Розмитнений", "обмін",
    "Потребує ремонту", "Після ДТП", "терміново", "Терміново",
)

# Відомі марки (uppercase) — використовуються для евристичного розпізнавання
# початку нової картки в текстовому потоці (fallback-парсер)
KNOWN_BRANDS = {
    "OPEL", "FORD", "ACURA", "AUDI", "MITSUBISHI", "MAZDA", "SEAT", "PEUGEOT",
    "TOYOTA", "VOLKSWAGEN", "BMW", "MERCEDES", "HYUNDAI", "KIA", "RENAULT",
    "SKODA", "NISSAN", "HONDA", "CHEVROLET", "VOLVO", "SUBARU", "LEXUS",
    "JEEP", "PORSCHE", "SUZUKI", "FIAT", "CITROEN", "DACIA", "DAEWOO",
    "INFINITI", "JAGUAR", "MINI", "ROVER", "SAAB", "SSANGYONG", "TESLA",
    "CHERY", "GEELY", "HAVAL", "ZAZ", "VAZ", "GAZ", "MAN", "IVECO",
    "SCANIA", "DAF", "ISUZU", "LAND", "ALFA", "BUICK", "CADILLAC",
    "CHRYSLER", "DODGE", "GMC", "LANCIA", "LINCOLN", "MASERATI",
    "SMART", "TATA", "UAZ",
}

# Регіональні slug для основних міст (спостережено /kiev/ — інші НЕ перевірені
# прямим запитом, це обґрунтоване припущення за аналогією; за потреби —
# передавайте RAW slug напряму в --city, він піде як є)
CITY_SLUGS: dict[str, str] = {
    "kyiv": "kiev", "kiev": "kiev", "київ": "kiev",
    "kharkiv": "harkov", "харків": "harkov",
    "odesa": "odessa", "одеса": "odessa",
    "dnipro": "dnepropetrovsk", "дніпро": "dnepropetrovsk",
    "lviv": "lvov", "львів": "lvov",
    "zaporizhzhia": "zaporozhye", "запоріжжя": "zaporozhye",
}


# ─── Дата-клас ────────────────────────────────────────────────────────────────

@dataclass
class RstCar:
    title:        str
    brand:        Optional[str]
    model:        Optional[str]
    year:         Optional[int]
    price_usd:    Optional[int]
    price_uah:    Optional[int]
    mileage_km:   Optional[int]
    transmission: Optional[str]
    fuel:         Optional[str]
    engine:       Optional[str]
    location:     Optional[str]
    tags:         list[str]        # "хороша ціна", "обмін", "Розмитнений" тощо
    is_top:       bool
    posted_ago:   Optional[str]    # "сьогодні", "вчора", "4 дня", "1 тиждень"
    url:          Optional[str]
    car_id:       Optional[int]


# ─── Парсер тексту картки (використовується і DOM-, і text-режимом) ──────────

def parse_card_text(text: str) -> dict:
    """
    Розбирає текст однієї картки авто на структуровані поля.

    Підтримує ОБИДВА спостережені формати:
      "OPEL Vectra•C · $6'500= 282'600 грн · 2007(325 тис) 2.8 Бенз(Авт) Київ · сьогодні, ТОП"
      "AUDI A4 · $13'700= 615'900 грн · 2015 р (226 тис) 2.0 Бенз (Авт) 226'000 km · Київська · 1 тиждень"
    """
    result: dict = {}

    # Ціна: "$3'150= 137'000 грн"
    price_m = re.search(r"\$([\d']+)=\s*([\d']+)\s*грн", text)
    if price_m:
        result["price_usd"] = int(price_m.group(1).replace("'", ""))
        result["price_uah"] = int(price_m.group(2).replace("'", ""))

    # Рік (+опц. "р") і пробіг у дужках "(263 тис)" одразу після
    year_m = re.search(
        r"\b(19[5-9]\d|20[0-2]\d)\b\s*р?\s*\(?(\d[\d\s']*)?\s*тис\)?", text
    )
    if year_m:
        result["year"] = int(year_m.group(1))
        if year_m.group(2):
            result["mileage_km"] = int(
                year_m.group(2).replace(" ", "").replace("'", "")
            ) * 1000
    else:
        year_m2 = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", text)
        if year_m2:
            result["year"] = int(year_m2.group(1))

    # Пробіг явно вказаний в км (перекриває оцінку з "тис", якщо є): "263'000 km"
    km_m = re.search(r"([\d']+)\s*km\b", text)
    if km_m:
        result["mileage_km"] = int(km_m.group(1).replace("'", ""))

    # Об'єм двигуна: число перед паливом
    engine_m = re.search(r"(\d\.\d)\s*(?:Диз|Бенз|Г/Б|Газ|Гібр|Електро)", text)
    if engine_m:
        result["engine"] = engine_m.group(1)

    # Паливо + коробка передач (в дужках, з пробілом або без)
    fuel_m = re.search(r"(Диз|Бенз|Г/Б|Газ|Гібр|Електро)\s*\((Авт|Мех|Роб|Вар)\)", text)
    if fuel_m:
        result["fuel"] = FUEL_ABBR.get(fuel_m.group(1), fuel_m.group(1))
        result["transmission"] = TRANS_ABBR.get(fuel_m.group(2), fuel_m.group(2))

    # Мітки/теги (стан, умови угоди)
    tags = [tag for tag in KNOWN_TAGS if tag.lower() in text.lower()]
    if tags:
        result["tags"] = tags

    # ТОП-оголошення
    result["is_top"] = bool(re.search(r"\bТОП\b", text))

    # Час публікації: "сьогодні", "вчора", "N дня/днів", "N тиждень/тижні/тижнів"
    time_m = re.search(
        r"(сьогодні|вчора|\d+\s*(?:день|дня|днів|тиждень|тижні|тижнів|"
        r"місяць|місяці|місяців))",
        text, re.IGNORECASE,
    )
    if time_m:
        result["posted_ago"] = time_m.group(0).strip()

    return result


def split_title(raw_title: str) -> tuple[Optional[str], Optional[str]]:
    """
    "OPEL Vectra•C" -> ("OPEL", "Vectra C")
    "AUDI A4"        -> ("AUDI", "A4")
    "PEUGEOT 605"    -> ("PEUGEOT", "605")
    """
    parts = raw_title.strip().split(None, 1)
    brand = parts[0] if parts else None
    model = parts[1].replace("•", " ").strip() if len(parts) > 1 else None
    return brand, model


# ─── Парсер ───────────────────────────────────────────────────────────────────

class RstParser:
    """
    Парсер каталогу rst.ua.

    Реалізує ДВА режими розбору сторінки:
      1. DOM-режим  — шукає <a href=".../brand_model_ID.html"> і читає текст
                       навколишнього блоку (як у car_market_parser/reono_parser).
      2. Text-режим — fallback: якщо DOM-режим не знайшов жодної картки,
                       розбиває суцільний текст сторінки на картки за допомогою
                       евристики "нова картка починається з відомого бренду".
                       Це страхує від того, що точна DOM-структура сайту не
                       була перевірена наживо (бот-захист блокує прямий огляд).
    """

    def __init__(self, delay: float = 1.2, verbose: bool = False):
        self.delay   = delay
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update(RST_HEADERS)
        self._warm_up()

    def _warm_up(self):
        try:
            r = self.session.get(RST_BASE_URL, timeout=15)
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

    # ── Побудова шляху фільтра ──────────────────────────────────────────────

    @staticmethod
    def build_path(
        city:  str | None = None,
        brand: str | None = None,
        model: str | None = None,
    ) -> str:
        """legkovoe-avto-стиль: ukr/oldcars/{city}/{brand}/{model}/"""
        segments = [CATALOG_PATH]
        if city:
            segments.append(_resolve_city(city))
        if brand:
            segments.append(_slugify(brand))
        if model:
            segments.append(_slugify(model))
        return "/".join(segments) + "/"

    # ── Режим 1: DOM-парсинг ────────────────────────────────────────────────

    def _parse_dom(self, soup: BeautifulSoup) -> list[RstCar]:
        cars: list[RstCar] = []
        seen_ids: set[int] = set()

        body = soup.find("body") or soup

        # Посилання на оголошення: .../brand_model_ID.html
        id_re = re.compile(r"_(\d+)\.html$")

        for a in body.find_all("a", href=True):
            href = a["href"]
            m = id_re.search(href)
            if not m:
                continue
            car_id = int(m.group(1))
            if car_id in seen_ids:
                continue

            # Текст картки: беремо найближчий контейнер-предок з достатнім
            # обсягом тексту (щоб охопити ціну/рік/паливо, а не лише заголовок)
            container = a
            block_text = ""
            for _ in range(4):  # піднімаємось до 4 рівнів вгору
                if container.parent is None:
                    break
                container = container.parent
                block_text = container.get_text(" ", strip=True)
                if "$" in block_text and re.search(r"\b(19|20)\d{2}\b", block_text):
                    break

            if not block_text:
                continue

            specs = parse_card_text(block_text)
            if "year" not in specs and "price_usd" not in specs:
                continue  # найімовірніше не картка авто, а навігаційне посилання

            title_text = a.get_text(" ", strip=True)
            brand, model = split_title(title_text) if title_text else (None, None)

            url = href if href.startswith("http") else RST_BASE_URL + "/" + href.lstrip("/")

            cars.append(RstCar(
                title=title_text or block_text[:40],
                brand=brand,
                model=model,
                year=specs.get("year"),
                price_usd=specs.get("price_usd"),
                price_uah=specs.get("price_uah"),
                mileage_km=specs.get("mileage_km"),
                transmission=specs.get("transmission"),
                fuel=specs.get("fuel"),
                engine=specs.get("engine"),
                location=None,
                tags=specs.get("tags", []),
                is_top=specs.get("is_top", False),
                posted_ago=specs.get("posted_ago"),
                url=url,
                car_id=car_id,
            ))
            seen_ids.add(car_id)

        return cars

    # ── Режим 2: text-fallback парсинг ──────────────────────────────────────

    def _parse_text_fallback(self, soup: BeautifulSoup) -> list[RstCar]:
        """
        Розбиває суцільний текст сторінки на картки авто за евристикою:
        нова картка починається там, де токен (розділений " · ") стартує
        з відомої марки (KNOWN_BRANDS) в верхньому регістрі.
        """
        full_text = soup.get_text(" · ", strip=True)
        tokens = [t.strip() for t in full_text.split(" · ") if t.strip()]

        cars: list[RstCar] = []
        current_title: Optional[str] = None
        current_tokens: list[str] = []

        def is_title_token(tok: str) -> bool:
            first_word = tok.split(None, 1)[0] if tok else ""
            return first_word.upper() in KNOWN_BRANDS

        def flush():
            nonlocal current_title, current_tokens
            if current_title and current_tokens:
                block_text = " · ".join(current_tokens)
                specs = parse_card_text(block_text)
                if "year" in specs or "price_usd" in specs:
                    brand, model = split_title(current_title)
                    cars.append(RstCar(
                        title=current_title,
                        brand=brand,
                        model=model,
                        year=specs.get("year"),
                        price_usd=specs.get("price_usd"),
                        price_uah=specs.get("price_uah"),
                        mileage_km=specs.get("mileage_km"),
                        transmission=specs.get("transmission"),
                        fuel=specs.get("fuel"),
                        engine=specs.get("engine"),
                        location=None,
                        tags=specs.get("tags", []),
                        is_top=specs.get("is_top", False),
                        posted_ago=specs.get("posted_ago"),
                        url=None,   # text-режим не дає посилань
                        car_id=None,
                    ))
            current_title = None
            current_tokens = []

        for tok in tokens:
            if is_title_token(tok):
                flush()
                current_title = tok
                current_tokens = []
            elif current_title is not None:
                current_tokens.append(tok)
                # Завершуємо картку після токена з часом публікації
                if re.search(
                    r"(сьогодні|вчора|\d+\s*(день|дня|днів|тиждень|тижні|тижнів))",
                    tok, re.IGNORECASE,
                ):
                    flush()

        flush()  # остання картка, якщо текст не закінчився часом публікації
        return cars

    # ── Завантаження сторінки ───────────────────────────────────────────────

    def fetch_page(self, path: str) -> tuple[list[RstCar], int]:
        url = f"{RST_BASE_URL}/{path}"
        soup = self._get(url)

        page_text = soup.get_text(" ", strip=True)
        total = 0
        m = re.search(r"([\d']+)\s*оголошень", page_text)
        if m:
            total = int(m.group(1).replace("'", ""))

        cars = self._parse_dom(soup)
        if not cars:
            if self.verbose:
                print("  [info] DOM-режим не знайшов карток, пробуємо text-fallback...",
                      file=sys.stderr)
            cars = self._parse_text_fallback(soup)

        return cars, total

    # ── Пошук ────────────────────────────────────────────────────────────────

    def search(
        self,
        city:  str | None = None,
        brand: str | None = None,
        model: str | None = None,
        pages: int = 1,
        min_price: int | None = None,
        max_price: int | None = None,
        year_from: int | None = None,
        year_to:   int | None = None,
    ) -> list[RstCar]:
        base_path = self.build_path(city=city, brand=brand, model=model)

        all_cars: list[RstCar] = []
        for page_num in range(1, pages + 1):
            # Пагінація НЕ підтверджена прямим запитом (сайт заблокував доступ) —
            # найімовірніший варіант за аналогією з іншими сторінками сайту:
            # числовий сегмент "/N.html" в кінці шляху. Якщо не спрацює —
            # --verbose покаже статус-код/довжину відповіді для діагностики.
            path = base_path if page_num == 1 else f"{base_path}{page_num}.html"

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

            if len(cars) == 0:
                break

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
        print("\n═══ ДІАГНОСТИКА rst.ua ═══\n")
        print("1. Перевірка доступності...")
        try:
            r = self.session.get(RST_BASE_URL, timeout=10)
            print(f"   Статус: {r.status_code}, довжина: {len(r.text)} байт")
            if r.status_code in (403, 429) or len(r.text) < 500:
                print("   ⚠ Схоже на бот-захист (Cloudflare/подібне).")
                print("   Спробуйте: pip install cloudscraper --break-system-packages")
                print("   і замініть requests.Session() на cloudscraper.create_scraper()")
        except Exception as e:
            print(f"   ПОМИЛКА: {e}")
            return

        print("\n2. Перевірка каталогу /ukr/oldcars/kiev/...")
        try:
            cars, total = self.fetch_page(f"{CATALOG_PATH}/kiev/")
            print(f"   Всього оголошень (з тексту сторінки): {total}")
            print(f"   Розпізнано карток: {len(cars)}")
            if cars:
                c = cars[0]
                print(f"\n3. Перше авто:")
                print(f"   {c.title} ({c.year}) — ${c.price_usd} / {c.price_uah}₴")
                print(f"   Пробіг: {c.mileage_km} км")
                print(f"   Коробка: {c.transmission}, Паливо: {c.fuel}, Двигун: {c.engine}")
                print(f"   Теги: {c.tags}, Top: {c.is_top}, Опубліковано: {c.posted_ago}")
                print(f"   URL: {c.url}")
            else:
                print("   [!] Жодної картки не розпізнано — DOM-структура сайту,")
                print("       ймовірно, відрізняється від припущеної. Перевірте --verbose")
                print("       і, за потреби, скоригуйте _parse_dom()/_parse_text_fallback().")
        except Exception as e:
            import traceback
            print(f"   ПОМИЛКА: {e}")
            traceback.print_exc()
        print("\n═══════════════════════════\n")


# ─── Допоміжні функції ────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def _resolve_city(city: str) -> str:
    key = city.strip().lower()
    return CITY_SLUGS.get(key, _slugify(city))


# ─── Вивід ────────────────────────────────────────────────────────────────────

def print_table(cars: list[RstCar]):
    if not cars:
        print("Авто не знайдено.")
        return

    W = 110
    print(f"\n{'═' * W}")
    print(f"  Знайдено авто: {len(cars)}")
    print(f"{'═' * W}")
    fmt = "{:<4} {:<26} {:>5} {:>9} {:>10} {:<14} {:<16} {:<18} {:<10}"
    print(fmt.format("★", "Назва", "Рік", "Ціна $", "Пробіг",
                      "Коробка", "Паливо", "Теги", "Коли"))
    print("─" * W)

    for c in cars:
        star = "★" if c.is_top else ""
        price = f"${c.price_usd:,}" if c.price_usd else "-"
        mileage = f"{c.mileage_km:,} км" if c.mileage_km else "-"
        tags = ", ".join(c.tags)[:17] if c.tags else "-"
        print(fmt.format(
            star,
            (c.title or "-")[:25],
            c.year or "-",
            price,
            mileage,
            (c.transmission or "-")[:13],
            (c.fuel or "-")[:15],
            tags,
            (c.posted_ago or "-")[:9],
        ))
    print(f"{'═' * W}\n")

    prices = [c.price_usd for c in cars if c.price_usd]
    if prices:
        print(f"  Ціна: мін ${min(prices):,}  |  макс ${max(prices):,}  |  "
              f"середня ${sum(prices)//len(prices):,}")
    print()


def print_json_output(cars: list[RstCar], output_file: Optional[str] = None):
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
        description="Парсер авторинку rst.ua",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--city",  help="Місто (kiev, kharkiv, odesa...)")
    p.add_argument("--brand", help="Марка (напр. opel, volkswagen)")
    p.add_argument("--model", help="Модель (напр. vectra, golf)")
    p.add_argument("--pages", type=int, default=1, help="Кількість сторінок")
    p.add_argument("--min-price", type=int, help="Мін. ціна $ (клієнтський фільтр)")
    p.add_argument("--max-price", type=int, help="Макс. ціна $ (клієнтський фільтр)")
    p.add_argument("--year-from", type=int, help="Рік від (клієнтський фільтр)")
    p.add_argument("--year-to",   type=int, help="Рік до (клієнтський фільтр)")
    p.add_argument("--output", "-o", help="Зберегти у JSON-файл")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.add_argument("--delay",  type=float, default=1.2)
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--diagnose", action="store_true")
    return p


def main():
    cli  = build_cli()
    args = cli.parse_args()

    parser = RstParser(delay=args.delay, verbose=args.verbose)

    if args.diagnose:
        parser.diagnose()
        return

    print("🔍 Пошук авто на rst.ua...", file=sys.stderr)

    cars = parser.search(
        city=args.city,
        brand=args.brand,
        model=args.model,
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