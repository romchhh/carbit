"""
Парсер auto.ria.com — з фокусом на BYD.

Як влаштоване API AUTO.RIA (вивчено наживо, без ключа):

1. Офіційний REST API (developers.ria.com) — вимагає реєстрації та api_key
   (user_id + api_key у query). Дає структурований JSON, але без ключа
   недоступний, тож для публічного скрапінгу не використовується.

2. Публічна сторінка пошуку (те, чим користується сам сайт і всі відомі
   community-скрапери, без жодного ключа):
     https://auto.ria.com/uk/search/?categories.main.id=1&brand.id[0]={ID}
   Пагінація: &page=N (з 0), &size=N (10/20/30/50/100 — видно у випадайці
   "Показувати по N пропозицій" внизу сторінки).
   На сторінці одразу видно кількість результатів ("557 пропозицій") і
   картки оголошень — кожна картка це одне посилання
   <a href="/uk/auto_{brand}_{model}_{id}.html"> з усім текстом картки
   всередині (назва, ціна, пробіг, паливо, місто, бейджі, короткий опис).

3. Сторінка самого оголошення (/uk/auto_{brand}_{model}_{id}.html) містить
   значно більше структурованих даних як пари "підпис на своєму рядку —
   значення на наступному": Двигун / Коробка передач / Привід / Колір,
   а також VIN-код, номерний знак, ціну в $ і грн, пробіг, локацію,
   дату створення оголошення, кількість переглядів, опис продавця, а також
   ПОВНУ галерею фото авто (усі знімки, не лише перший/обкладинка).
   Ці дані і тягне enrich_with_details().

4. Легасі-API марок (без ключа, використовується для визначення ID бренду
   за назвою): http://api.auto.ria.com/categories/1/marks
   Повертає [{"name": "BMW", "value": 9}, ...]. BYD на момент написання
   має value=386 (перевірено наживо через реальний пошук).

ВАЖЛИВО про фото: сторінка пошуку (картка оголошення) містить лише ОДНЕ
превʼю-фото в DOM. Повний список усіх фото авто є тільки на сторінці самого
оголошення, тому він доступний виключно при --details (fetch_car_details
збирає їх у car.photos — список URL — і дублює перше у car.photo_url для
зворотної сумісності). Без --details поле car.photos лишається порожнім.

Використання (гортання сторінок та довантаження деталей/фото — УВІМКНЕНІ
за замовчуванням, нічого додатково вказувати не треба):
  python autoria_byd_parser.py                          # BYD; після кожної сторінки питає в консолі, чи йти далі
  python autoria_byd_parser.py --brand bmw               # інший бренд (резолв ID через API марок)
  python autoria_byd_parser.py --brand-id 386             # явний ID бренду
  python autoria_byd_parser.py --no-interactive --pages 5 # без запитань, рівно 5 сторінок
  python autoria_byd_parser.py --no-details               # швидше, без фото/повних деталей
  python autoria_byd_parser.py --min-price 15000 --max-price 30000
  python autoria_byd_parser.py --output byd.json
  python autoria_byd_parser.py --diagnose --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup


# ─── Константи ────────────────────────────────────────────────────────────────

BASE_URL   = "https://auto.ria.com"
SEARCH_URL = f"{BASE_URL}/uk/search/"
MARKS_API  = "http://api.auto.ria.com/categories/{category_id}/marks"

CATEGORY_LEGKOVI = 1  # легкові авто

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
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Referer": BASE_URL,
}

# Підтверджені наживо ID марок (categories.main.id=1, легкові).
# Для будь-якої іншої марки скрипт сам зверне до MARKS_API і знайде ID за назвою.
KNOWN_BRAND_IDS: dict[str, int] = {
    "byd": 386,
}

# Дозволяємо і дефіс, і підкреслення в слазі моделі (сайт віддає обидва варіанти:
# .../auto_byd_song-plus_40307001.html та .../auto_byd_song_plus_40307001.html),
# а також екранований JSON-вигляд слеша (\/), який трапляється всередині
# вбудованих <script type="application/json"> блоків Next.js/React.
LISTING_URL_RE = re.compile(r"/uk/auto_[a-z0-9_\-]+_(\d+)\.html", re.IGNORECASE)
LISTING_ID_RAW_RE = re.compile(
    r"auto_[a-z0-9_\-]+_(\d+)\.html", re.IGNORECASE
)
VIN_RE   = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
PLATE_RE = re.compile(r"\b[A-ZА-ЯІЇЄ]{2}\s?\d{4}\s?[A-ZА-ЯІЇЄ]{2}\b")
PRICE_USD_UAH_RE = re.compile(r"([\d\s]{3,})\s*\$\s*[•·]\s*([\d\s]{3,})\s*грн")
PRICE_USD_ONLY_RE = re.compile(r"([\d\s]{3,})\s*\$")
MILEAGE_RE = re.compile(r"([\d\s]+)\s*тис\.?\s*км")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")

FUEL_WORDS  = ["Електро", "Бензин", "Дизель", "Гібрид", "Газ"]
TRANS_WORDS = ["Автомат", "Механіка", "Ручна", "Типтронік", "Робот", "Варіатор"]
DRIVE_WORDS = ["Передній", "Задній", "Повний"]


# ─── Дата-класи ───────────────────────────────────────────────────────────────

@dataclass
class Car:
    car_id:       int
    url:          str
    brand:        Optional[str]
    model:        Optional[str]
    year:         Optional[int]
    price_usd:    Optional[int]
    price_uah:    Optional[int]
    mileage_km:   Optional[int]
    city:         Optional[str]
    fuel:         Optional[str]
    transmission: Optional[str]
    drive:        Optional[str]
    color:        Optional[str]
    vin:          Optional[str]
    plate:        Optional[str]
    body_type:    Optional[str]
    is_dealer:    Optional[bool]
    seller_name:  Optional[str]
    posted:       Optional[str]
    views:        Optional[int]
    description:  Optional[str]
    photo_url:    Optional[str]
    raw_card_text: Optional[str] = None
    # Повний список URL усіх фото авто (заповнюється лише при --details,
    # бо повна галерея доступна тільки на сторінці самого оголошення).
    photos:       list[str] = field(default_factory=list)
    details:      dict = field(default_factory=dict)


# ─── Парсер ───────────────────────────────────────────────────────────────────

class AutoRiaParser:

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

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        if self.verbose:
            q = "&".join(f"{k}={v}" for k, v in (params or {}).items())
            print(f"  → GET {url}{'?' + q if q else ''}", file=sys.stderr)
        resp = self.session.get(url, params=params, timeout=20)
        if self.verbose:
            print(f"  ← {resp.status_code} ({len(resp.text)} байт)", file=sys.stderr)
        resp.raise_for_status()
        time.sleep(self.delay)
        return resp

    # ── Резолв ID бренду ─────────────────────────────────────────────────────

    def resolve_brand_id(self, brand_name: str) -> int:
        key = brand_name.strip().lower()
        if key in KNOWN_BRAND_IDS:
            return KNOWN_BRAND_IDS[key]
        try:
            url = MARKS_API.format(category_id=CATEGORY_LEGKOVI)
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            marks = r.json()
            for m in marks:
                if str(m.get("name", "")).strip().lower() == key:
                    return int(m["value"])
        except Exception as e:
            if self.verbose:
                print(f"  [warn] не вдалось резолвнути бренд через MARKS_API: {e}",
                      file=sys.stderr)
        raise ValueError(
            f"Не вдалось визначити ID бренду '{brand_name}'. "
            f"Знайдіть його вручну: відкрийте auto.ria.com, оберіть марку у фільтрі "
            f"і подивіться на brand.id[0]=... у адресному рядку, потім передайте "
            f"--brand-id <ID>."
        )

    # ── Пошук ────────────────────────────────────────────────────────────────

    def fetch_search_page(self, brand_id: int, page: int, size: int,
                           dump_html_to: str | None = None) -> tuple[BeautifulSoup, int, str]:
        params = {
            "categories.main.id": CATEGORY_LEGKOVI,
            "brand.id[0]": brand_id,
            "page": page,
            "size": size,
        }
        resp = self._get(SEARCH_URL, params=params)
        raw_html = resp.text

        if dump_html_to:
            with open(dump_html_to, "w", encoding="utf-8") as f:
                f.write(raw_html)
            print(f"  [diag] Сирий HTML збережено у {dump_html_to} "
                  f"({len(raw_html)} байт)", file=sys.stderr)
            has_next_data = "__NEXT_DATA__" in raw_html
            has_apollo = "__APOLLO_STATE__" in raw_html
            anchor_count = len(re.findall(r'<a\s[^>]*href="[^"]*auto_', raw_html))
            raw_id_count = len(set(LISTING_ID_RAW_RE.findall(raw_html)))
            print(f"  [diag] __NEXT_DATA__ у HTML: {has_next_data}", file=sys.stderr)
            print(f"  [diag] __APOLLO_STATE__ у HTML: {has_apollo}", file=sys.stderr)
            print(f"  [diag] <a href=...auto_...> тегів у сирому HTML: {anchor_count}",
                  file=sys.stderr)
            print(f"  [diag] унікальних ID оголошень (по всьому HTML, регуляркою): "
                  f"{raw_id_count}", file=sys.stderr)

        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(" ", strip=True)
        total = 0
        m = re.search(r"([\d\s]{1,7})\s*пропозиц", text)
        if m:
            total = int(m.group(1).replace(" ", "").replace("\xa0", ""))
        return soup, total, raw_html

    def _parse_search_card(self, a_tag) -> Optional[Car]:
        href = a_tag.get("href", "")
        m = LISTING_URL_RE.search(href)
        if not m:
            return None
        car_id = int(m.group(1))
        url = href if href.startswith("http") else BASE_URL + href

        # brand/model зі слага URL: /uk/auto_byd_song-plus_40307001.html
        slug = href.rstrip("/").split("/")[-1].replace(".html", "")
        parts = slug.split("_")
        brand = parts[1] if len(parts) > 1 else None
        model = "-".join(parts[2:-1]).replace("-", " ").title() if len(parts) > 3 else None

        text = a_tag.get_text(" ", strip=True)
        if not text:
            return None

        year_m = YEAR_RE.search(text)
        year = int(year_m.group()) if year_m else None

        price_usd = price_uah = None
        pm = PRICE_USD_UAH_RE.search(text)
        if pm:
            price_usd = int(pm.group(1).replace(" ", "").replace("\xa0", ""))
            price_uah = int(pm.group(2).replace(" ", "").replace("\xa0", ""))
        else:
            pm2 = PRICE_USD_ONLY_RE.search(text)
            if pm2:
                price_usd = int(pm2.group(1).replace(" ", "").replace("\xa0", ""))

        mileage_km = None
        mm = MILEAGE_RE.search(text)
        if mm:
            mileage_km = int(float(mm.group(1).replace(" ", "").replace("\xa0", "")) * 1000)

        fuel = next((w for w in FUEL_WORDS if w in text), None)
        transmission = next((w for w in TRANS_WORDS if w in text), None)
        drive = next((w for w in DRIVE_WORDS if w in text), None)
        is_dealer = "Перевірений дилер" in text
        vin_present = "Перевірений VIN" in text

        img = a_tag.find("img")
        photo_url = None
        if img:
            src = img.get("src") or img.get("data-src")
            if src:
                photo_url = src if src.startswith("http") else None

        return Car(
            car_id=car_id,
            url=url,
            brand=brand,
            model=model,
            year=year,
            price_usd=price_usd,
            price_uah=price_uah,
            mileage_km=mileage_km,
            city=None,          # точний парсинг міста — ненадійний з тексту картки, див. --details
            fuel=fuel,
            transmission=transmission,
            drive=drive,
            color=None,
            vin=("присутній" if vin_present else None),
            plate=None,
            body_type=None,
            is_dealer=is_dealer,
            seller_name=None,
            posted=None,
            views=None,
            description=None,
            photo_url=photo_url,
            raw_card_text=text[:500],
        )

    def search(
        self,
        brand: str | None = None,
        brand_id: int | None = None,
        pages: int = 1,
        size: int = 100,
        min_price: int | None = None,
        max_price: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        interactive: bool = False,
        details: bool = False,
    ) -> tuple[list[Car], int]:
        if brand_id is None:
            if not brand:
                raise ValueError("Потрібно вказати --brand або --brand-id")
            brand_id = self.resolve_brand_id(brand)

        all_cars: list[Car] = []
        total = 0
        seen_ids: set[int] = set()

        # В інтерактивному режимі гортаємо сторінки, поки є результати і
        # користувач сам не зупинить (--pages тоді ігнорується як точна межа
        # і використовується лише як дуже великий запобіжний ліміт).
        max_pages = 10_000 if interactive else pages

        page = 0
        while page < max_pages:
            print(f"  Завантаження сторінки {page}...", file=sys.stderr)
            try:
                soup, total, raw_html = self.fetch_search_page(brand_id, page, size)
            except Exception as e:
                print(f"  [!] Помилка на сторінці {page}: {e}", file=sys.stderr)
                break

            page_cars: list[Car] = []

            # Основний шлях: справжні <a href="...auto_...html"> теги з текстом картки.
            for a in soup.find_all("a", href=LISTING_URL_RE):
                car = self._parse_search_card(a)
                if car and car.car_id not in seen_ids:
                    page_cars.append(car)
                    seen_ids.add(car.car_id)

            # Фолбек: якщо анкорів немає (типовий випадок для JS-рендерених
            # сторінок — картки підвантажуються фронтендом окремим запитом,
            # і простий requests.get() бачить лише "скелет" сторінки), все одно
            # витягуємо ID+URL прямо з сирого HTML/вбудованого JSON регуляркою.
            # Це не дає ціни/пробігу/т.д., але дає хоча б список авто.
            if not page_cars:
                for m in LISTING_ID_RAW_RE.finditer(raw_html):
                    car_id = int(m.group(1))
                    if car_id in seen_ids:
                        continue
                    slug_match = re.search(
                        r"auto_([a-z0-9_\-]+)_" + str(car_id) + r"\.html",
                        raw_html, re.IGNORECASE)
                    slug = slug_match.group(1) if slug_match else ""
                    slug_parts = slug.split("_")
                    brand_guess = slug_parts[0] if slug_parts else None
                    model_guess = " ".join(slug_parts[1:]).replace("-", " ").title() \
                        if len(slug_parts) > 1 else None
                    page_cars.append(Car(
                        car_id=car_id,
                        url=f"{BASE_URL}/uk/auto_{slug}_{car_id}.html",
                        brand=brand_guess, model=model_guess, year=None,
                        price_usd=None, price_uah=None, mileage_km=None,
                        city=None, fuel=None, transmission=None, drive=None,
                        color=None, vin=None, plate=None, body_type=None,
                        is_dealer=None, seller_name=None, posted=None,
                        views=None, description=None, photo_url=None,
                    ))
                    seen_ids.add(car_id)
                if page_cars:
                    print(f"  [info] <a> теги не знайдені (JS-рендер) — "
                          f"{len(page_cars)} ID/URL здобуто фолбеком по сирому HTML. "
                          f"Запусти з --details, щоб дотягнути ціну/пробіг/фото/т.д. "
                          f"з кожної сторінки оголошення.", file=sys.stderr)
                else:
                    print("  [warn] Жодного ID оголошення не знайдено навіть фолбеком. "
                          "Запусти --diagnose --verbose, щоб зберегти сирий HTML "
                          "і розібратись, чому.", file=sys.stderr)

            all_cars.extend(page_cars)

            print(f"  Сторінка {page}: розпізнано {len(page_cars)} карток "
                  f"(всього за фільтром на сайті: {total})", file=sys.stderr)

            # Довантажуємо повні дані/фото ОДРАЗУ для щойно зібраної сторінки —
            # а не лише в кінці після всього гортання, — щоб у --interactive
            # було видно реальні фото вже на першій сторінці, перш ніж
            # вирішувати, чи гортати далі.
            if details and page_cars:
                self.enrich_with_details(page_cars)

            no_more = (not page_cars) or (len(all_cars) >= total)

            if interactive:
                # Показуємо саме щойно завантажену сторінку окремо, щоб було
                # зручно гортати й вирішувати, чи йти далі.
                print_table(page_cars)
                print_ids(page_cars, label=f"ID на сторінці {page}")

            page += 1

            if no_more:
                break

            if interactive:
                if page >= max_pages:
                    print("  Досягнуто запобіжного ліміту сторінок.", file=sys.stderr)
                    break
                if not _ask_yes_no(f"➡️  Перейти до сторінки {page + 1}? [Y/n] "):
                    print("  Гортання зупинено користувачем.", file=sys.stderr)
                    break

        # Локальна пост-фільтрація (сайтові параметри ціни/року у публічному
        # пошуку без сесії/JS не завжди стабільно приймаються, тож фільтруємо тут).
        def keep(c: Car) -> bool:
            if min_price is not None and (c.price_usd is None or c.price_usd < min_price):
                return False
            if max_price is not None and (c.price_usd is None or c.price_usd > max_price):
                return False
            if year_from is not None and (c.year is None or c.year < year_from):
                return False
            if year_to is not None and (c.year is None or c.year > year_to):
                return False
            return True

        if any(v is not None for v in (min_price, max_price, year_from, year_to)):
            before = len(all_cars)
            all_cars = [c for c in all_cars if keep(c)]
            print(f"  Локальний фільтр: {before} → {len(all_cars)}", file=sys.stderr)

        print_ids(all_cars, label="ID зібраних оголошень (після пошуку)")

        return all_cars, total

    # ── Деталі оголошення ────────────────────────────────────────────────────

    @staticmethod
    def _label_value(lines: list[str], label: str) -> Optional[str]:
        try:
            idx = lines.index(label)
        except ValueError:
            return None
        for nxt in lines[idx + 1: idx + 3]:
            if nxt and nxt != label:
                return nxt
        return None

    def fetch_car_details(self, car: Car) -> dict:
        """
        Витягує МАКСИМУМ даних зі сторінки оголошення. Сторінка організована
        як послідовність пар "підпис на своєму рядку → значення на наступному",
        плюс кілька явних секцій (опції, VIN-перевірка, продавець, фото,
        схожі оголошення). Все, що вдалось розпізнати, лягає в car.details.
        Повний список фото додатково дублюється у car.photos.
        """
        try:
            resp = self._get(car.url)
        except Exception as e:
            if self.verbose:
                print(f"  [warn] не вдалось завантажити {car.url}: {e}", file=sys.stderr)
            return {}

        # Знімаємо JSON-екранування слешів: частина URL фото сидить у вбудованому
        # JSON (стан гідратації React/Next.js) у вигляді "https:\/\/cdn0.ria...",
        # і звичайний regex з прямими слешами такі рядки просто не бачить.
        raw_html = resp.text.replace("\\/", "/")
        soup = BeautifulSoup(raw_html, "html.parser")
        details: dict = {}

        details["meta_description"] = _meta_content(soup, "description")
        details["meta_keywords"] = _meta_content(soup, "keywords")
        details["og_title"] = _meta_content(soup, "og:title", prop=True)
        details["og_image"] = _meta_content(soup, "og:image", prop=True)
        car.photo_url = car.photo_url or details["og_image"]

        full_text = soup.get_text(" ", strip=True)
        lines = [l.strip() for l in soup.get_text("\n", strip=True).split("\n") if l.strip()]

        # ── Базові поля (як і раніше) ────────────────────────────────────────
        vin_m = VIN_RE.search(full_text)
        if vin_m:
            car.vin = vin_m.group(0)
        plate_m = PLATE_RE.search(full_text)
        if plate_m:
            car.plate = plate_m.group(0)
        price_m = PRICE_USD_UAH_RE.search(full_text)
        if price_m:
            car.price_usd = int(price_m.group(1).replace(" ", "").replace("\xa0", ""))
            car.price_uah = int(price_m.group(2).replace(" ", "").replace("\xa0", ""))
        mil_m = MILEAGE_RE.search(full_text)
        if mil_m:
            car.mileage_km = int(float(mil_m.group(1).replace(" ", "").replace("\xa0", "")) * 1000)
        car.fuel = self._label_value(lines, "Двигун") or car.fuel
        car.transmission = self._label_value(lines, "Коробка передач") or car.transmission
        car.drive = self._label_value(lines, "Привід") or car.drive
        car.color = self._label_value(lines, "Колір")
        loc_m = re.search(r"UA,\s*([^,]+),\s*([^,]+),\s*\d{5}", full_text)
        if loc_m:
            car.city = loc_m.group(2).strip()
            details["region"] = loc_m.group(1).strip()
        body_m = re.search(
            r"(Седан|Хетчбек|Універсал|Купе|Мінівен|Пікап|Ліфтбек|"
            r"Позашляховик\s*/\s*Кросовер|Кабріолет)", full_text)
        if body_m:
            car.body_type = body_m.group(1)
        car.is_dealer = ("Перевірений дилер" in full_text) or car.is_dealer

        # ── Двері / місця / покоління / комплектація / модифікація ─────────
        doors_seats_m = re.search(r"•\s*(\d+)\s*дверей\s*•\s*(\d+)\s*місць", full_text)
        if doors_seats_m:
            details["doors"] = int(doors_seats_m.group(1))
            details["seats"] = int(doors_seats_m.group(2))
        details["generation_trim"] = self._label_value(
            lines, "Покоління, комплектація, модифікація")
        details["technical_condition"] = self._label_value(lines, "Технічний стан")

        # ── Стан авто (badge-рядок після "Стан") ────────────────────────────
        condition_line = self._label_value(lines, "Стан")
        if condition_line and "•" in condition_line:
            details["condition_flags"] = [s.strip() for s in condition_line.split("•")]
        elif condition_line:
            details["condition_flags"] = [condition_line]

        # ── Блоки опцій: підпис-секція → один рядок з "•"-переліком ─────────
        option_sections = [
            "Безпека", "Комфорт", "Оптика", "Система допомоги при паркуванні",
            "Подушка безпеки",
        ]
        options: dict[str, list[str]] = {}
        for section in option_sections:
            val = self._label_value(lines, section)
            if val:
                options[section] = [s.strip() for s in val.split("•")]
        # Одиночні (не •-списком) параметри салону/керма
        salon: dict[str, str] = {}
        for label in [
            "Колір салону", "Регулювання сидінь салону по висоті", "Вентиляція сидінь",
            "Підігрів сидінь", "Памʼять положення сидіння", "Електросклопідйомники",
            "Кондиціонер", "Підсилювач керма", "Регулювання керма",
        ]:
            val = self._label_value(lines, label)
            if val:
                salon[label] = val
        if salon:
            options["Салон"] = salon
        if options:
            details["options"] = options

        # ── Електричні характеристики (для EV/PHEV) ─────────────────────────
        if "Електричні характеристики" in full_text:
            electric: dict = {}
            electric["battery_capacity"] = self._label_value(lines, "Ємність акумулятора")
            range_line = self._label_value(lines, "Запас ходу, км/100%")
            if range_line:
                electric["range_km_100pct"] = range_line
            electric["battery_health_soh"] = self._label_value(lines, "Здоровʼя акумулятора (SOH)")
            battery_state = self._label_value(lines, "Стан акумулятора")
            if battery_state:
                electric["battery_state"] = battery_state
            electric["energy_efficiency"] = self._label_value(lines, "Енергоефективність")
            electric["motor_power"] = self._label_value(lines, "Потужність двигуна")
            # Зарядний розʼєм — значення часто йде як два послідовні рядки-іконки
            try:
                idx = lines.index("Зарядний розʼєм")
                connectors = [l for l in lines[idx + 1: idx + 4]
                              if l and "Зарядний" not in l and len(l) < 30]
                if connectors:
                    electric["charging_connector"] = connectors
            except ValueError:
                pass
            details["electric"] = {k: v for k, v in electric.items() if v}

        # ── Продавець ─────────────────────────────────────────────────────
        seller: dict = {}
        seller_name = self._label_value(lines, "Продавець")
        if seller_name:
            seller["name"] = seller_name
        rating_m = re.search(r"([\d.]+)\s*з\s*5\s*рейтинг", full_text)
        if rating_m:
            seller["rating"] = float(rating_m.group(1))
        reviews_m = re.search(r"(\d+)\s*відгук", full_text)
        if reviews_m:
            seller["reviews_count"] = int(reviews_m.group(1))
        years_m = re.search(r"(\d+\+?)\s*років?\s*працює\s*з\s*AUTO\.RIA", full_text)
        if years_m:
            seller["years_on_platform"] = years_m.group(1)
        if "Підтверджено через Дію" in full_text:
            seller["verified_via_diia"] = True
        if seller:
            car.seller_name = seller.get("name", car.seller_name)
            details["seller"] = seller

        # ── VIN-перевірка AUTO.RIA (застави / пробіг / ДТП) ─────────────────
        vin_check: dict = {}
        if "Перевірено AUTO.RIA по VIN-коду" in full_text:
            pledge_type = self._label_value(lines, "Тип обтяження")
            pledge_restriction = self._label_value(lines, "Обмеження відчуження")
            last_checked_mileage = self._label_value(lines, "Останній перевірений пробіг")
            seller_mileage = self._label_value(lines, "Пробіг від продавця")
            accidents = self._label_value(lines, "ДТП")
            insurance_cases = self._label_value(lines, "Страхові випадки в Україні")
            vin_check = {
                "pledge_type": pledge_type,
                "pledge_restriction": pledge_restriction,
                "last_checked_mileage": last_checked_mileage,
                "seller_stated_mileage": seller_mileage,
                "accidents_registered": accidents,
                "insurance_cases": insurance_cases,
            }
            vin_check = {k: v for k, v in vin_check.items() if v}
        owners_m = re.search(r"(\d+)\s*власник", full_text)
        if owners_m:
            vin_check["owners_count"] = int(owners_m.group(1))
        last_op_m = re.search(r"Остання операція\s*(\d{2}\.\d{2}\.\d{4})\s*•\s*([^0-9]+?)"
                               r"(?=Опис від продавця|\d+\s*власник|$)", full_text)
        if last_op_m:
            vin_check["last_registration_date"] = last_op_m.group(1)
            vin_check["last_registration_type"] = last_op_m.group(2).strip()
        if "Відсутній у розшуку" in full_text:
            vin_check["wanted_status"] = "не в розшуку"
        if vin_check:
            details["vin_check"] = vin_check

        # ── Опис продавця ────────────────────────────────────────────────
        desc_m = re.search(r"Опис від продавця\s*(.+?)(?:Позашляховик|Седан|Хетчбек|Універсал|"
                            r"Купе|Мінівен|Покоління|$)", full_text)
        if desc_m:
            car.description = desc_m.group(1).strip()[:1500]

        # ── Статистика оголошення ───────────────────────────────────────
        id_m = re.search(r"ID авто\s*(\d+)", full_text)
        views_m = re.search(r"Переглядів авто\s*([\d\s]+)", full_text)
        favorites_m = re.search(r"Додано в Обране\s*([\d\s]+)", full_text)
        created_m = re.search(r"Оголошення створене\s*(\d{2}\.\d{2}\.\d{4})", full_text)
        if views_m:
            car.views = int(views_m.group(1).replace(" ", "").replace("\xa0", ""))
        if created_m:
            car.posted = created_m.group(1)
        details["stats"] = {
            "ad_id": int(id_m.group(1)) if id_m else car.car_id,
            "views": car.views,
            "favorites": int(favorites_m.group(1).replace(" ", "")) if favorites_m else None,
            "created": car.posted,
        }

        # ── Всі фото авто ────────────────────────────────────────────────
        # ВАЖЛИВО (причина, чому раніше було лише 1 фото): видима карусель
        # оголошення — це віртуалізований Swiper-слайдер. У сирому HTML без
        # виконання JS у ньому реально присутні лише перші кілька <img src=...>,
        # решта слайдів — порожні заглушки, які браузер заповнює по мірі
        # гортання. Регуляркою по cdn*.riastatic.com з такої сторінки
        # витягувались тільки ці кілька "видимих" фото.
        #
        # Натомість AUTO.RIA (як і більшість маркетплейсів) додатково рендерить
        # на сервері JSON-LD блок (<script type="application/ld+json">) зі
        # структурованими даними оголошення для Google/пошукових систем —
        # і саме там лежить ПОВНИЙ список фото ("image": [...]), незалежно
        # від JS-каруселі. Це і є основне джерело нижче; регулярка по HTML
        # лишається як доповнення/фолбек.
        photos_full: list[str] = []
        seen_photo_ids: set[str] = set()
        size_rank = {"hd": 3, "bx": 2, "fx": 1, "cx": 0}

        def _photo_id(u: str) -> str:
            m = re.search(r"__(\d+)[a-z]{1,3}\.\w+$", u)
            return m.group(1) if m else u

        def _photo_rank(u: str) -> int:
            m = re.search(r"__\d+([a-z]{1,3})\.\w+$", u)
            return size_rank.get(m.group(1), 0) if m else 0

        def _add_photo(u: str) -> None:
            if not u:
                return
            if u.startswith("//"):
                u = "https:" + u
            if not u.startswith("http"):
                return
            pid = _photo_id(u)
            if pid not in seen_photo_ids:
                photos_full.append(u)
                seen_photo_ids.add(pid)
            else:
                # замінюємо на більшу версію, якщо знайшли кращу (hd > bx > fx > cx)
                for i, existing in enumerate(photos_full):
                    if _photo_id(existing) == pid:
                        if _photo_rank(u) > _photo_rank(existing):
                            photos_full[i] = u
                        break

        def _walk_json_for_photos(obj) -> None:
            if isinstance(obj, str):
                if "riastatic.com" in obj and re.search(
                        r"\.(?:jpe?g|webp|png)(?:$|\?)", obj, re.IGNORECASE):
                    _add_photo(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _walk_json_for_photos(v)
            elif isinstance(obj, list):
                for v in obj:
                    _walk_json_for_photos(v)

        # 1) Основне джерело: рекурсивний обхід УСІХ вбудованих JSON-блоків
        #    сторінки (як application/json — типово __NEXT_DATA__/hydration-
        #    стан, так і application/ld+json — SEO-розмітка). Рекурсивний
        #    обхід навмисно не прив'язаний до конкретного імені поля (image,
        #    photos, gallery тощо) — так надійніше на випадок, якщо AUTO.RIA
        #    поміняє структуру, і саме тут з великою ймовірністю лежить
        #    повний масив фото, яким живиться JS-карусель.
        json_scripts_found = 0
        for script_tag in soup.find_all("script"):
            script_type = (script_tag.get("type") or "").lower()
            if script_type not in ("application/json", "application/ld+json"):
                continue
            raw_json = script_tag.string or script_tag.get_text()
            if not raw_json or not raw_json.strip():
                continue
            try:
                parsed = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                continue
            json_scripts_found += 1
            _walk_json_for_photos(parsed)

        photos_from_json = len(photos_full)

        # 2) Доповнення/фолбек: регулярка по всьому сирому HTML (ловить фото,
        #    яких немає у вбудованих JSON-блоках — напр. якщо їх там нема
        #    взагалі, або сторінка змінить розмітку).
        for u in re.findall(
            r"(?:https?:)?//cdn\d*\.riastatic\.com/[^\s\"'\\)]+?\.(?:jpe?g|webp|png)",
            raw_html, re.IGNORECASE,
        ):
            _add_photo(u)

        details["photos"] = sorted(set(photos_full))
        details["photos_count"] = len(details["photos"])

        # Ця діагностика друкується завжди (не лише при --verbose), бо саме
        # вона показує, чи справді знайдено всі фото авто в консолі.
        print(f"    [{car.car_id}] {car.brand or '-'} {car.model or '-'}: "
              f"JSON-блоків знайдено {json_scripts_found}, фото з JSON "
              f"{photos_from_json}, всього фото після фолбеку "
              f"{len(details['photos'])}", file=sys.stderr)

        # Дублюємо повний список фото прямо в об'єкт Car (не лише в details),
        # щоб він був доступний одразу як car.photos, а не лише вкладено.
        if details["photos"]:
            car.photos = details["photos"]
            if not car.photo_url:
                car.photo_url = car.photos[0]

        # ── Схожі оголошення ─────────────────────────────────────────────
        similar = []
        for a in soup.find_all("a", href=LISTING_URL_RE):
            m2 = LISTING_URL_RE.search(a.get("href", ""))
            if not m2:
                continue
            sim_id = int(m2.group(1))
            if sim_id == car.car_id:
                continue
            txt = a.get_text(" ", strip=True)
            price_m2 = PRICE_USD_ONLY_RE.search(txt)
            similar.append({
                "id": sim_id,
                "url": BASE_URL + a["href"] if a["href"].startswith("/") else a["href"],
                "text": txt[:150],
                "price_usd": int(price_m2.group(1).replace(" ", "")) if price_m2 else None,
            })
            if len(similar) >= 12:
                break
        if similar:
            details["similar_listings"] = similar

        details["fetched_at_unix"] = int(time.time())
        details = {k: v for k, v in details.items() if v not in (None, {}, [], "")}
        return details

    def enrich_with_details(self, cars: list[Car]) -> None:
        if not cars:
            return
        print(f"  Завантаження деталей: {len(cars)} оголошень...", file=sys.stderr)
        for i, car in enumerate(cars, 1):
            car.details = self.fetch_car_details(car)
            if i % 10 == 0 or i == len(cars):
                print(f"    деталі: {i}/{len(cars)}", file=sys.stderr)
        print_ids(cars, label="ID оголошень з довантаженими деталями/фото")

    # ── Діагностика ──────────────────────────────────────────────────────────

    def diagnose(self, brand: str, brand_id: int | None):
        print(f"\n═══ ДІАГНОСТИКА auto.ria.com ═══\n")
        bid = brand_id or self.resolve_brand_id(brand)
        print(f"1. Бренд '{brand}' → ID {bid}")
        try:
            soup, total, raw_html = self.fetch_search_page(
                bid, page=0, size=20, dump_html_to="autoria_search_dump.html")
            print(f"2. Знайдено на сайті: {total} оголошень")
            anchors = soup.find_all("a", href=LISTING_URL_RE)
            print(f"3. Розпізнано карток (<a> теги): {len(anchors)}")
            raw_ids = sorted(set(int(x) for x in LISTING_ID_RAW_RE.findall(raw_html)))
            print(f"3б. ID оголошень фолбеком по сирому HTML: {len(raw_ids)}")
            if raw_ids:
                print(f"    перші 5 ID: {raw_ids[:5]}")
            if anchors:
                car = self._parse_search_card(anchors[0])
                print("\n4. Перше авто (з картки пошуку):")
                for k, v in asdict(car).items():
                    if k in ("details", "raw_card_text"):
                        continue
                    print(f"   {k}: {v}")
                print("\n5. Завантажую деталі цього оголошення...")
                car.details = self.fetch_car_details(car)
                print("\n6. Авто після enrich_with_details:")
                for k, v in asdict(car).items():
                    if k in ("details", "raw_card_text", "description"):
                        continue
                    print(f"   {k}: {v}")
        except Exception as e:
            import traceback
            print(f"   ПОМИЛКА: {e}")
            traceback.print_exc()
        print("\n═══════════════════════════════════\n")


# ─── Допоміжні функції ────────────────────────────────────────────────────────

def _meta_content(soup: BeautifulSoup, key: str, prop: bool = False) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": key}) if prop else soup.find("meta", attrs={"name": key})
    return tag.get("content") if tag else None


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Питає користувача так/ні в консолі (для гортання сторінок).
    При EOF/Ctrl+C (наприклад, скрипт запущено не інтерактивно) — зупиняє
    гортання, повертаючи False, замість того щоб впасти з помилкою."""
    try:
        ans = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not ans:
        return default
    return ans in ("y", "yes", "т", "так", "да", "d", "1")


def print_ids(cars: list[Car], label: str = "ID спарсених оголошень") -> None:
    """Виводить у консоль (stdout) відсортований список ID усіх зібраних авто."""
    ids = sorted(c.car_id for c in cars)
    print(f"\n{label} ({len(ids)}):")
    print(", ".join(str(i) for i in ids) if ids else "(порожньо)")
    print()


def print_table(cars: list[Car]):
    if not cars:
        print("Авто не знайдено.")
        return
    W = 118
    print(f"\n{'═' * W}")
    print(f"  Показано авто: {len(cars)}")
    print(f"{'═' * W}")
    fmt = "{:<10} {:<14} {:>5} {:>10} {:>10} {:<9} {:<9} {:<8} {:>6} {}"
    print(fmt.format("Бренд", "Модель", "Рік", "Ціна $", "Пробіг", "Паливо", "КПП", "Дилер", "Фото", "ID"))
    print("─" * W)
    for c in cars:
        price_str = f"${c.price_usd:,}" if c.price_usd else "-"
        mileage_str = f"{c.mileage_km // 1000} тис.км" if c.mileage_km else "-"
        photos_str = str(len(c.photos)) if c.photos else "-"
        print(fmt.format(
            (c.brand or "-")[:9],
            (c.model or "-")[:13],
            c.year or "-",
            price_str,
            mileage_str,
            (c.fuel or "-")[:8],
            (c.transmission or "-")[:8],
            "так" if c.is_dealer else "ні",
            photos_str,
            c.car_id,
        ))
    print(f"{'═' * W}\n")
    prices = [c.price_usd for c in cars if c.price_usd]
    if prices:
        print(f"  Ціна: мін ${min(prices):,}  |  макс ${max(prices):,}  "
              f"|  середня ${sum(prices) // len(prices):,}")
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
        description="Парсер auto.ria.com (фокус на BYD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--brand", default="byd", help="Назва марки (за замовч. byd)")
    p.add_argument("--brand-id", type=int, help="Явний числовий ID марки (пропускає резолв)")
    p.add_argument("--pages", type=int, default=1,
                   help="Кількість сторінок пошуку. У режимі гортання (за замовчуванням "
                        "увімкнено) ігнорується як точне число і використовується лише "
                        "як запобіжна межа.")
    p.add_argument("--interactive", "-i", dest="interactive", action="store_true",
                   default=True,
                   help="Інтерактивне гортання сторінок у консолі: показує щойно "
                        "завантажену сторінку і питає, чи перейти до наступної. "
                        "УВІМКНЕНО за замовчуванням.")
    p.add_argument("--no-interactive", dest="interactive", action="store_false",
                   help="Вимкнути гортання — завантажити рівно --pages сторінок "
                        "без запитань (для автоматизації/cron).")
    p.add_argument("--size", type=int, default=100, choices=[10, 20, 30, 50, 100],
                   help="Оголошень на сторінку (як у фільтрі сайту)")
    p.add_argument("--min-price", type=int, metavar="$")
    p.add_argument("--max-price", type=int, metavar="$")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--details", dest="details", action="store_true", default=True,
                   help="Довантажити повні дані й усі фото з кожної сторінки "
                        "оголошення (повільніше). УВІМКНЕНО за замовчуванням.")
    p.add_argument("--no-details", dest="details", action="store_false",
                   help="Вимкнути довантаження деталей/фото — лише дані з картки "
                        "пошуку (швидше).")
    p.add_argument("--output", "-o", metavar="FILE")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Додаткові технічні логи (запити, HTTP-статуси тощо). "
                        "Діагностика по фото друкується в консоль незалежно від цього прапорця.")
    p.add_argument("--diagnose", action="store_true")
    return p


def main():
    args = build_cli().parse_args()
    parser = AutoRiaParser(delay=args.delay, verbose=args.verbose)

    if args.diagnose:
        parser.diagnose(brand=args.brand, brand_id=args.brand_id)
        return

    print(f"🔍 Пошук '{args.brand}' на auto.ria.com...", file=sys.stderr)

    if not args.details:
        print("ℹ️  --no-details: повний список фото (car.photos) буде порожнім — "
              "картка пошуку містить лише одне превʼю-фото на авто.", file=sys.stderr)

    cars, total = parser.search(
        brand=args.brand,
        brand_id=args.brand_id,
        pages=args.pages,
        size=args.size,
        min_price=args.min_price,
        max_price=args.max_price,
        year_from=args.year_from,
        year_to=args.year_to,
        interactive=args.interactive,
        details=args.details,
    )

    # Головна вимога: чітко показати кількість знайдених авто.
    print(f"\n✅ Знайдено оголошень за фільтром на сайті: {total}")
    print(f"✅ Зібрано (розпарсено) карток: {len(cars)}\n")

    output_file = args.output or f"autoria_{args.brand}_{int(time.time())}.json"
    print_json_output(cars, output_file)

    if args.format == "table":
        print_table(cars)

    print_ids(cars, label="Підсумковий список ID усіх спарсених авто")

    print(f"JSON output: {output_file}")


if __name__ == "__main__":
    main()