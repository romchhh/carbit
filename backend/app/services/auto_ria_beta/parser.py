"""HTML-парсер auto.ria.com (логіка з cartest4.py)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from app.services.auto_ria_beta.constants import BASE_URL

LISTING_URL_RE = re.compile(r"/uk/auto_[a-z0-9_\-]+_(\d+)\.html", re.IGNORECASE)
LISTING_ID_RAW_RE = re.compile(r"auto_[a-z0-9_\-]+_(\d+)\.html", re.IGNORECASE)
VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
PLATE_RE = re.compile(r"\b[A-ZА-ЯІЇЄ]{2}\s?\d{4}\s?[A-ZА-ЯІЇЄ]{2}\b")
PRICE_USD_UAH_RE = re.compile(r"([\d\s]{3,})\s*\$\s*[•·]\s*([\d\s]{3,})\s*грн")
PRICE_USD_ONLY_RE = re.compile(r"([\d\s]{3,})\s*\$")
MILEAGE_RE = re.compile(r"([\d\s]+)\s*тис\.?\s*км")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")

FUEL_WORDS = ["Електро", "Бензин", "Дизель", "Гібрид", "Газ"]
TRANS_WORDS = ["Автомат", "Механіка", "Ручна", "Типтронік", "Робот", "Варіатор"]
DRIVE_WORDS = ["Передній", "Задній", "Повний"]


@dataclass
class ScrapedCar:
    car_id: int
    url: str
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    price_usd: int | None = None
    price_uah: int | None = None
    mileage_km: int | None = None
    city: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    drive: str | None = None
    color: str | None = None
    vin: str | None = None
    plate: str | None = None
    body_type: str | None = None
    is_dealer: bool | None = None
    seller_name: str | None = None
    posted: str | None = None
    views: int | None = None
    description: str | None = None
    photo_url: str | None = None
    photos: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def parse_total_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    match = re.search(r"([\d\s]{1,7})\s*пропозиц", text)
    if not match:
        return 0
    return int(match.group(1).replace(" ", "").replace("\xa0", ""))


def parse_search_page(html: str) -> tuple[list[ScrapedCar], int]:
    total = parse_total_count(html)
    soup = BeautifulSoup(html, "html.parser")
    cars: list[ScrapedCar] = []
    seen: set[int] = set()

    for anchor in soup.find_all("a", href=LISTING_URL_RE):
        car = _parse_search_card(anchor)
        if car and car.car_id not in seen:
            cars.append(car)
            seen.add(car.car_id)

    if not cars:
        for match in LISTING_ID_RAW_RE.finditer(html):
            car_id = int(match.group(1))
            if car_id in seen:
                continue
            slug_match = re.search(
                r"auto_([a-z0-9_\-]+)_" + str(car_id) + r"\.html",
                html,
                re.IGNORECASE,
            )
            slug = slug_match.group(1) if slug_match else ""
            slug_parts = slug.split("_")
            brand_guess = slug_parts[0] if slug_parts else None
            model_guess = (
                " ".join(slug_parts[1:]).replace("-", " ").title()
                if len(slug_parts) > 1
                else None
            )
            cars.append(
                ScrapedCar(
                    car_id=car_id,
                    url=f"{BASE_URL}/uk/auto_{slug}_{car_id}.html",
                    brand=brand_guess,
                    model=model_guess,
                )
            )
            seen.add(car_id)

    return cars, total


def _parse_search_card(anchor) -> ScrapedCar | None:
    href = anchor.get("href", "")
    match = LISTING_URL_RE.search(href)
    if not match:
        return None

    car_id = int(match.group(1))
    url = href if href.startswith("http") else BASE_URL + href
    slug = href.rstrip("/").split("/")[-1].replace(".html", "")
    parts = slug.split("_")
    brand = parts[1] if len(parts) > 1 else None
    model = "-".join(parts[2:-1]).replace("-", " ").title() if len(parts) > 3 else None
    text = anchor.get_text(" ", strip=True)
    if not text:
        return None

    year_match = YEAR_RE.search(text)
    year = int(year_match.group()) if year_match else None

    price_usd = price_uah = None
    price_match = PRICE_USD_UAH_RE.search(text)
    if price_match:
        price_usd = int(price_match.group(1).replace(" ", "").replace("\xa0", ""))
        price_uah = int(price_match.group(2).replace(" ", "").replace("\xa0", ""))
    else:
        usd_only = PRICE_USD_ONLY_RE.search(text)
        if usd_only:
            price_usd = int(usd_only.group(1).replace(" ", "").replace("\xa0", ""))

    mileage_km = None
    mileage_match = MILEAGE_RE.search(text)
    if mileage_match:
        mileage_km = int(float(mileage_match.group(1).replace(" ", "").replace("\xa0", "")) * 1000)

    img = anchor.find("img")
    photo_url = None
    if img:
        src = img.get("src") or img.get("data-src")
        if src and str(src).startswith("http"):
            photo_url = str(src)

    return ScrapedCar(
        car_id=car_id,
        url=url,
        brand=brand,
        model=model,
        year=year,
        price_usd=price_usd,
        price_uah=price_uah,
        mileage_km=mileage_km,
        fuel=next((word for word in FUEL_WORDS if word in text), None),
        transmission=next((word for word in TRANS_WORDS if word in text), None),
        drive=next((word for word in DRIVE_WORDS if word in text), None),
        is_dealer="Перевірений дилер" in text,
        vin="present" if "Перевірений VIN" in text else None,
        photo_url=photo_url,
    )


def _label_value(lines: list[str], label: str) -> str | None:
    try:
        idx = lines.index(label)
    except ValueError:
        return None
    for nxt in lines[idx + 1 : idx + 3]:
        if nxt and nxt != label:
            return nxt
    return None


def parse_listing_details(html: str, car: ScrapedCar) -> dict[str, Any]:
    raw_html = html.replace("\\/", "/")
    soup = BeautifulSoup(raw_html, "html.parser")
    details: dict[str, Any] = {}
    full_text = soup.get_text(" ", strip=True)
    lines = [line.strip() for line in soup.get_text("\n", strip=True).split("\n") if line.strip()]

    vin_match = VIN_RE.search(full_text)
    if vin_match:
        car.vin = vin_match.group(0)
    plate_match = PLATE_RE.search(full_text)
    if plate_match:
        car.plate = plate_match.group(0)

    price_match = PRICE_USD_UAH_RE.search(full_text)
    if price_match:
        car.price_usd = int(price_match.group(1).replace(" ", "").replace("\xa0", ""))
        car.price_uah = int(price_match.group(2).replace(" ", "").replace("\xa0", ""))

    mileage_match = MILEAGE_RE.search(full_text)
    if mileage_match:
        car.mileage_km = int(float(mileage_match.group(1).replace(" ", "").replace("\xa0", "")) * 1000)

    car.fuel = _label_value(lines, "Двигун") or car.fuel
    car.transmission = _label_value(lines, "Коробка передач") or car.transmission
    car.drive = _label_value(lines, "Привід") or car.drive
    car.color = _label_value(lines, "Колір")

    location_match = re.search(r"UA,\s*([^,]+),\s*([^,]+),\s*\d{5}", full_text)
    if location_match:
        car.city = location_match.group(2).strip()
        details["region"] = location_match.group(1).strip()

    photos = _extract_photos(raw_html, soup)
    if photos:
        car.photos = photos
        car.photo_url = car.photo_url or photos[0]
        details["photos"] = photos

    description_match = re.search(
        r"Опис від продавця\s*(.+?)(?:Позашляховик|Седан|Хетчбек|Універсал|"
        r"Купе|Мінівен|Покоління|$)",
        full_text,
    )
    if description_match:
        car.description = description_match.group(1).strip()[:1500]

    views_match = re.search(r"Переглядів авто\s*([\d\s]+)", full_text)
    if views_match:
        car.views = int(views_match.group(1).replace(" ", "").replace("\xa0", ""))
    created_match = re.search(r"Оголошення створене\s*(\d{2}\.\d{2}\.\d{4})", full_text)
    if created_match:
        car.posted = created_match.group(1)

    return {key: value for key, value in details.items() if value not in (None, {}, [], "")}


def _extract_photos(raw_html: str, soup: BeautifulSoup) -> list[str]:
    photos: list[str] = []
    seen_ids: set[str] = set()
    size_rank = {"hd": 3, "bx": 2, "fx": 1, "cx": 0}

    def photo_id(url: str) -> str:
        match = re.search(r"__(\d+)[a-z]{1,3}\.\w+$", url)
        return match.group(1) if match else url

    def photo_rank(url: str) -> int:
        match = re.search(r"__\d+([a-z]{1,3})\.\w+$", url)
        return size_rank.get(match.group(1), 0) if match else 0

    def add_photo(url: str) -> None:
        if not url:
            return
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            return
        pid = photo_id(url)
        if pid not in seen_ids:
            photos.append(url)
            seen_ids.add(pid)
        else:
            for index, existing in enumerate(photos):
                if photo_id(existing) == pid and photo_rank(url) > photo_rank(existing):
                    photos[index] = url
                    break

    def walk_json(obj: Any) -> None:
        if isinstance(obj, str):
            if "riastatic.com" in obj and re.search(r"\.(?:jpe?g|webp|png)(?:$|\?)", obj, re.IGNORECASE):
                add_photo(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                walk_json(value)
        elif isinstance(obj, list):
            for value in obj:
                walk_json(value)

    for script_tag in soup.find_all("script"):
        script_type = (script_tag.get("type") or "").lower()
        if script_type not in ("application/json", "application/ld+json"):
            continue
        raw_json = script_tag.string or script_tag.get_text()
        if not raw_json or not raw_json.strip():
            continue
        try:
            walk_json(json.loads(raw_json))
        except (json.JSONDecodeError, TypeError):
            continue

    for url in re.findall(
        r"(?:https?:)?//cdn\d*\.riastatic\.com/[^\s\"'\\)]+?\.(?:jpe?g|webp|png)",
        raw_html,
        re.IGNORECASE,
    ):
        add_photo(url)

    return photos
