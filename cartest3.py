"""
Парсер lubeavto.com.ua — авторинок "Любе Авто" (Львів).

Сайт: Next.js SSR (App Router). Три каталоги:
  /store/instore        — Авто в наявності (на майданчику)
  /store/instoreusers   — Авто в дорозі (в дорозі з аукціонів/митниці)
  /store/auction        — Авто з аукціонів (лоти, ще не викуплені)

Кожна картка авто містить (у такому порядку в DOM):
  бейдж (напр. "НОВЕ")
  VIN (17 символів)
  фото-посилання <a href="/store/instore/ID"><img></a>
  заголовок <h4><a href="/store/instore/ID">Марка Модель Рік</a></h4>
  ціна "19 500 $"
  пробіг "93 тис. км" (або "-", якщо не вказано)
  паливо "Бензин" / "Дизель" / "Електро" / "Гібрид" / "Газ"
  об'єм двигуна "2.0 л" (або "77 kWh" для електро)
  рік (окремим числом)
  коробка передач "Автомат" / "Механіка" / "Робот" / "Варіатор"
  привід "Передній" / "Задній" / "Повний"
  посилання "Переглянути автомобіль" + порожнє посилання "order-car"

Фільтрація по бренду/моделі — через сегменти шляху:
  /store/instore/audi
  /store/instore/audi/a4
Пагінація — через query-параметр ?pageNumber=N (нумерація з 0).

ПРИМІТКА: точні CSS-класи карток на сайті невідомі (динамічний Next.js білд,
класи можуть змінюватись між релізами). Тому картки виокремлюються
структурно — від заголовного <a href="/store/instore/{id}"><h4>...</h4></a>
підіймаємось по батьківських тегах, поки контейнер не міститиме рівно одну
картку (одна ціна "$", один <h4>). Якщо верстка сайту суттєво зміниться —
запустіть --diagnose --verbose і підправте регулярні вирази в _parse_specs.

Використання:
  python lubeavto_parser.py                                  # всі авто в наявності, 1 стор.
  python lubeavto_parser.py --brand audi                     # тільки Audi
  python lubeavto_parser.py --brand audi --model a4          # тільки Audi A4
  python lubeavto_parser.py --catalog instoreusers           # авто в дорозі
  python lubeavto_parser.py --catalog auction                # авто з аукціонів
  python lubeavto_parser.py --pages 5                        # 5 сторінок
  python lubeavto_parser.py --min-price 10000 --max-price 20000
  python lubeavto_parser.py --output cars.json
  python lubeavto_parser.py --diagnose --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


# ─── Константи ────────────────────────────────────────────────────────────────

BASE_URL = "https://lubeavto.com.ua"

CATALOGS = {
    "instore":      "store/instore",       # Авто в наявності
    "instoreusers": "store/instoreusers",  # Авто в дорозі
    "auction":      "store/auction",       # Авто з аукціонів
}

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
    "DNT": "1",
    "Referer": BASE_URL,
}

FUEL_WORDS = ["Бензин", "Дизель", "Гібрид", "Електро", "Газ"]
TRANS_WORDS = ["Автомат", "Механіка", "Робот", "Варіатор", "Типтронік"]
DRIVE_WORDS = ["Передній", "Задній", "Повний"]

VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
CARD_ID_RE = re.compile(r"^/store/(?:instore|instoreusers|auction)/(\d+)$")


# ─── Дата-клас для авто ───────────────────────────────────────────────────────

@dataclass
class Car:
    title:        str
    brand:        Optional[str]
    model:        Optional[str]
    year:         Optional[int]
    price_usd:    Optional[int]
    mileage_km:   Optional[int]
    mileage_raw:  Optional[str]
    fuel:         Optional[str]
    engine:       Optional[str]
    transmission: Optional[str]
    drive:        Optional[str]
    vin:          Optional[str]
    badge:        Optional[str]
    url:          str
    image_url:    Optional[str]
    car_id:       Optional[int]
    details:      dict = field(default_factory=dict)


# ─── Парсер ───────────────────────────────────────────────────────────────────

class LubeAvtoParser:

    def __init__(self, catalog: str = "instore", delay: float = 1.0, verbose: bool = False):
        if catalog not in CATALOGS:
            raise ValueError(f"Невідомий каталог '{catalog}'. Доступні: {list(CATALOGS)}")
        self.catalog = catalog
        self.delay   = delay
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._warm_up()

    def _warm_up(self):
        try:
            r = self.session.get(BASE_URL, timeout=15)
            if self.verbose:
                print(f"[warm-up] {r.status_code}, cookies: {dict(self.session.cookies)}",
                      file=sys.stderr)
        except Exception as e:
            print(f"[warn] warm-up failed: {e}", file=sys.stderr)
        time.sleep(0.5)

    def _catalog_path(self, brand: str | None = None, model: str | None = None) -> str:
        path = CATALOGS[self.catalog]
        if brand:
            path += "/" + quote(brand.strip().lower())
            if model:
                path += "/" + quote(model.strip().lower())
        return f"{BASE_URL}/{path}"

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

    # ── Виокремлення контейнера картки ───────────────────────────────────────

    def _find_card_container(self, title_a):
        """
        Піднімається від заголовного <a> (з <h4> всередині) по батьках,
        поки не знайде контейнер, що містить рівно одну ціну ("$")
        і рівно один <h4> — тобто рівно одну картку авто.
        """
        node = title_a
        for _ in range(6):
            parent = node.parent
            if parent is None:
                break
            text = parent.get_text(" ", strip=True)
            h4_count = len(parent.find_all("h4"))
            price_count = len(re.findall(r"\d[\d\s]*\$", text))
            if h4_count == 1 and price_count == 1:
                node = parent
                continue
            if h4_count >= 2 or price_count >= 2:
                # Пішли занадто високо — контейнер вже містить кілька карток.
                return node if node is not title_a else parent
            node = parent
        return node

    # ── Парсинг однієї картки ────────────────────────────────────────────────

    def _parse_card(self, title_a, container) -> Optional[Car]:
        try:
            href = title_a.get("href", "")
            m = CARD_ID_RE.match(href)
            car_id = int(m.group(1)) if m else None
            url = href if href.startswith("http") else BASE_URL + href

            h4 = title_a.find("h4") or title_a
            title = h4.get_text(" ", strip=True)

            year_match = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", title)
            year = int(year_match.group()) if year_match else None
            name_part = title[:year_match.start()].strip() if year_match else title
            brand = name_part.split()[0] if name_part else None
            model = " ".join(name_part.split()[1:]) if len(name_part.split()) > 1 else None

            img = title_a.find("img") or container.find("img")
            image_url = None
            if img:
                src = img.get("src") or img.get("data-src")
                if src:
                    image_url = src if src.startswith("http") else BASE_URL + src

            full_text = container.get_text(" ", strip=True)

            vin_match = VIN_RE.search(full_text)
            vin = vin_match.group(0) if vin_match else None

            # Бейдж — слово(а) до VIN (якщо VIN присутній), інакше None.
            badge = None
            if vin_match:
                pre = full_text[:vin_match.start()].strip()
                if pre:
                    badge = pre.split(" ")[-1]

            # Якщо рік не знайшли в заголовку — беремо перше окреме число-рік у тексті.
            if year is None:
                y2 = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", full_text)
                if y2:
                    year = int(y2.group())

            price = None
            price_match = re.search(r"([\d\s]+)\$", full_text)
            if price_match:
                price = int(price_match.group(1).replace("\xa0", "").replace(" ", ""))

            mileage_raw = None
            mileage_km = None
            mil_match = re.search(r"([\d\s]+)\s*тис\.?\s*км", full_text)
            if mil_match:
                mileage_raw = mil_match.group(0).strip()
                num = float(mil_match.group(1).replace(" ", "").replace("\xa0", ""))
                mileage_km = int(num * 1000) if num < 1500 else int(num)

            fuel = next((w for w in FUEL_WORDS if w in full_text), None)
            transmission = next((w for w in TRANS_WORDS if w in full_text), None)
            drive = next((w for w in DRIVE_WORDS if w in full_text), None)

            engine = None
            eng_match = re.search(r"(\d+\.\d+)\s*(л|kWh|кВт·г)", full_text)
            if eng_match:
                engine = eng_match.group(0).strip()

            return Car(
                title=title,
                brand=brand,
                model=model,
                year=year,
                price_usd=price,
                mileage_km=mileage_km,
                mileage_raw=mileage_raw,
                fuel=fuel,
                engine=engine,
                transmission=transmission,
                drive=drive,
                vin=vin,
                badge=badge,
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

    # ── Завантаження сторінки ────────────────────────────────────────────────

    def fetch_page(self, brand: str | None, model: str | None, page_number: int) -> tuple[list[Car], int]:
        """Повертає (список_авто, total_count) для однієї сторінки каталогу."""
        url = self._catalog_path(brand, model)
        params = {"pageNumber": str(page_number)} if page_number else None
        soup = self._get(url, params=params)

        total = 0
        total_match = re.search(r"Знайдено\s+([\d\s]+)\s+результат", soup.get_text())
        if total_match:
            total = int(total_match.group(1).replace(" ", ""))

        if self.verbose:
            print(f"  [total] Знайдено {total} авто за фільтром", file=sys.stderr)

        cars: list[Car] = []
        seen_ids: set[int] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = CARD_ID_RE.match(href)
            if not m or not a.find("h4"):
                continue  # це не заголовне посилання картки

            car_id = int(m.group(1))
            if car_id in seen_ids:
                continue

            container = self._find_card_container(a)
            car = self._parse_card(a, container)
            if car:
                cars.append(car)
                seen_ids.add(car_id)

        return cars, total

    # ── Деталі зі сторінки авто ──────────────────────────────────────────────

    def _fetch_car_details(self, car: Car) -> dict:
        try:
            soup = self._get(car.url)
        except Exception as e:
            if self.verbose:
                print(f"  [warn] detail fail for {car.url}: {e}", file=sys.stderr)
            return {}

        details: dict = {}
        details["page_title"] = soup.title.get_text(strip=True) if soup.title else None
        details["meta_description"] = _meta_content(soup, "description")
        details["og_image"] = _meta_content(soup, "og:image", prop=True)

        images: list[str] = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            full = src if src.startswith("http") else BASE_URL + src
            if "storage-lavto" in full and full not in images:
                images.append(full)
        details["images"] = images
        details["images_count"] = len(images)
        if not car.image_url and images:
            car.image_url = images[0]

        # Комплектація/опис зазвичай іде суцільним текстовим блоком нижче фото.
        body_text = soup.get_text(" ", strip=True)
        feat_match = re.search(r"Комплектація:?\s*(.+?)(?:Переглянути|Замовити|$)", body_text)
        if feat_match:
            details["features_raw"] = feat_match.group(1).strip()[:1000]

        details["fetched_at_unix"] = int(time.time())
        return details

    def enrich_with_details(self, cars: list[Car]) -> None:
        if not cars:
            return
        print(f"  Завантаження деталей по авто: {len(cars)} шт...", file=sys.stderr)
        for i, car in enumerate(cars, 1):
            car.details = self._fetch_car_details(car)
            if i % 10 == 0 or i == len(cars):
                print(f"    деталі: {i}/{len(cars)}", file=sys.stderr)

    # ── Пошук ────────────────────────────────────────────────────────────────

    def search(
        self,
        brand:      str | None = None,
        model:      str | None = None,
        min_price:  int | None = None,
        max_price:  int | None = None,
        year_from:  int | None = None,
        year_to:    int | None = None,
        fuel:       str | None = None,
        pages:      int        = 1,
    ) -> list[Car]:
        """
        Пошук авто. Фільтри по ціні/року/паливу застосовуються локально
        (пост-фільтрація), бо точні query-параметри бекенду сайту невідомі —
        вони не видні у SSR-версії сторінки без виконання JS-фільтрів.
        Якщо потрібна фільтрація на боці сервера — перевірте --diagnose,
        яка мережева адреса викликається фронтендом при виборі фільтра
        (Network tab у DevTools), і додайте відповідні params у _get().
        """
        all_cars: list[Car] = []

        for page_num in range(pages):
            print(f"  Завантаження сторінки {page_num}...", file=sys.stderr)
            try:
                cars, total = self.fetch_page(brand, model, page_num)
            except Exception as e:
                print(f"  [!] Помилка: {e}", file=sys.stderr)
                break

            all_cars.extend(cars)
            print(f"  Знайдено {len(cars)} авто на сторінці {page_num} "
                  f"(всього за фільтром: {total})", file=sys.stderr)

            if not cars or (total and len(all_cars) >= total):
                break

        # Локальна пост-фільтрація
        def keep(c: Car) -> bool:
            if min_price is not None and (c.price_usd is None or c.price_usd < min_price):
                return False
            if max_price is not None and (c.price_usd is None or c.price_usd > max_price):
                return False
            if year_from is not None and (c.year is None or c.year < year_from):
                return False
            if year_to is not None and (c.year is None or c.year > year_to):
                return False
            if fuel is not None and (c.fuel is None or fuel.lower() not in c.fuel.lower()):
                return False
            return True

        if any(v is not None for v in (min_price, max_price, year_from, year_to, fuel)):
            before = len(all_cars)
            all_cars = [c for c in all_cars if keep(c)]
            print(f"  Локальний фільтр: {before} → {len(all_cars)} авто", file=sys.stderr)

        return all_cars

    # ── Діагностика ──────────────────────────────────────────────────────────

    def diagnose(self, brand: str | None = None, model: str | None = None):
        print(f"\n═══ ДІАГНОСТИКА lubeavto.com.ua [{self.catalog}] ═══\n")
        try:
            r = self.session.get(BASE_URL, timeout=10)
            print(f"1. Головна сторінка: статус {r.status_code}, {len(r.text)} байт")
        except Exception as e:
            print(f"   ПОМИЛКА: {e}")
            return

        try:
            cars, total = self.fetch_page(brand, model, 0)
            print(f"\n2. Каталог {self._catalog_path(brand, model)}:")
            print(f"   Всього результатів (заявлено сайтом): {total}")
            print(f"   Розпізнано карток на сторінці: {len(cars)}")
            if cars:
                c = cars[0]
                print(f"\n3. Перше авто:")
                for k, v in asdict(c).items():
                    if k == "details":
                        continue
                    print(f"   {k}: {v}")
            else:
                print("   [!] Жодної картки не розпізнано — верстка сайту могла змінитись.")
                print("       Запустіть з --verbose, щоб побачити сирий HTML-запит,")
                print("       і перевірте CARD_ID_RE / _find_card_container.")
        except Exception as e:
            import traceback
            print(f"   ПОМИЛКА: {e}")
            traceback.print_exc()

        print("\n═══════════════════════════════════\n")


# ─── Допоміжні функції ────────────────────────────────────────────────────────

def _meta_content(soup: BeautifulSoup, key: str, prop: bool = False) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": key}) if prop else soup.find("meta", attrs={"name": key})
    return tag.get("content") if tag else None


# ─── Вивід результатів ────────────────────────────────────────────────────────

def print_table(cars: list[Car]):
    if not cars:
        print("Авто не знайдено.")
        return

    W = 110
    print(f"\n{'═' * W}")
    print(f"  Знайдено авто: {len(cars)}")
    print(f"{'═' * W}")

    fmt = "{:<28} {:>5} {:>10} {:>12} {:<9} {:<9} {:<10} {:<9} {}"
    print(fmt.format("Назва", "Рік", "Ціна $", "Пробіг", "Паливо", "КПП", "Привід", "Бейдж", "VIN"))
    print("─" * W)

    for c in cars:
        price_str = f"${c.price_usd:,}" if c.price_usd else "-"
        mileage_str = c.mileage_raw or "-"
        print(fmt.format(
            (c.title or "-")[:27],
            c.year or "-",
            price_str,
            mileage_str,
            (c.fuel or "-")[:8],
            (c.transmission or "-")[:8],
            (c.drive or "-")[:9],
            (c.badge or "-")[:8],
            c.vin or "-",
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
        description="Парсер авторинку lubeavto.com.ua",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--catalog", choices=list(CATALOGS), default="instore",
                   help="instore=в наявності, instoreusers=в дорозі, auction=з аукціонів")
    p.add_argument("--brand", help="Марка авто, напр. audi, bmw, land-rover")
    p.add_argument("--model", help="Модель авто, напр. a4 (використовується разом із --brand)")
    p.add_argument("--min-price", type=int, metavar="$")
    p.add_argument("--max-price", type=int, metavar="$")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--fuel", help="Бензин / Дизель / Гібрид / Електро / Газ")
    p.add_argument("--pages", type=int, default=1, help="Кількість сторінок (за замовч. 1)")
    p.add_argument("--details", action="store_true", help="Підтягувати деталі з кожної сторінки авто")
    p.add_argument("--output", "-o", metavar="FILE", help="Зберегти у JSON-файл")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--diagnose", action="store_true")
    return p


def main():
    args = build_cli().parse_args()

    parser = LubeAvtoParser(catalog=args.catalog, delay=args.delay, verbose=args.verbose)

    if args.diagnose:
        parser.diagnose(brand=args.brand, model=args.model)
        return

    print("🔍 Пошук авто на lubeavto.com.ua...", file=sys.stderr)

    cars = parser.search(
        brand=args.brand,
        model=args.model,
        min_price=args.min_price,
        max_price=args.max_price,
        year_from=args.year_from,
        year_to=args.year_to,
        fuel=args.fuel,
        pages=args.pages,
    )

    if args.details:
        parser.enrich_with_details(cars)

    output_file = args.output or f"lubeavto_{args.catalog}_{int(time.time())}.json"
    print_json_output(cars, output_file)

    if args.format == "table":
        print_table(cars)
    print(f"JSON output: {output_file}")


if __name__ == "__main__":
    main()