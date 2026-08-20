from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.services.reono.constants import (
    FUEL_LABELS,
    GEARBOX_LABELS,
    REONO_BASE_URL,
)

_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
_TOTAL_RES = (
    re.compile(r"Найдено:?\s*([\d\s]+)\s*авто", re.IGNORECASE),
    re.compile(r"Знайдено:?\s*([\d\s]+)\s*авто", re.IGNORECASE),
)


@dataclass
class ReonoCar:
    title: str
    brand: Optional[str]
    model: Optional[str]
    year: Optional[int]
    price_usd: Optional[int]
    price_uah: Optional[int]
    mileage_km: Optional[int]
    is_new: bool
    transmission: Optional[str]
    fuel: Optional[str]
    engine: Optional[str]
    location: Optional[str]
    is_premium: bool
    url: str
    image_url: Optional[str]
    car_id: Optional[int]
    details: dict = field(default_factory=dict)


def _normalize_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return REONO_BASE_URL + (href if href.startswith("/") else f"/{href}")


def _listing_slug(href: str) -> Optional[str]:
    href = (href or "").strip()
    if not href:
        return None
    path = urlparse(href).path if href.startswith("http") else href.lstrip("/")
    path = path.strip("/")
    if not path or "/" in path:
        return None
    if not re.search(r"-\d+$", path):
        return None
    if path.startswith(("legkovoe-avto", "gruzovoj", "info", "catalog", "profile", "announcement")):
        return None
    return path


def _parse_int(value: object) -> Optional[int]:
    if value is None:
        return None
    text = str(value).replace(" ", "").replace("\xa0", "")
    if not text.isdigit():
        return None
    return int(text)


def _parse_car_card(card: Tag) -> Optional[ReonoCar]:
    car_id = _parse_int(card.get("data-announcement-id"))
    if not car_id:
        return None

    brand = (card.get("data-announcement-brand") or "").strip() or None
    model = (card.get("data-announcement-model") or "").strip() or None

    context: dict = {}
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
        url = _normalize_url(title_el["href"])
    if not url:
        link = card.select_one("a[data-announcement-link][href]")
        if link:
            url = _normalize_url(link.get("href", ""))
    if not url:
        url = f"{REONO_BASE_URL}/{brand or 'auto'}-{model or 'car'}-{car_id}".lower()

    year = _parse_int(context.get("year_range"))
    if year is None and title:
        year_match = _YEAR_RE.search(title)
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
    mileage_hint = context.get("mileage_range")
    mileage_val = _parse_int(mileage_hint)
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
    transmission = GEARBOX_LABELS.get(gearbox)
    if not transmission:
        for tag in card.select(".car-card__tag"):
            txt = tag.get_text(" ", strip=True)
            low = txt.lower()
            if any(word in low for word in ("автомат", "механ", "варіатор", "робот", "типтрон")):
                transmission = txt
                break

    fuel_key = str(context.get("fuel_type") or "").lower()
    fuel = FUEL_LABELS.get(fuel_key)
    engine = None
    for tag in card.select(".car-card__tag"):
        txt = tag.get_text(" ", strip=True)
        if "км" in txt.lower():
            continue
        fuel_match = re.search(
            r"(бензин|дизель|газ|гібрид|електро|метан)\s*,?\s*(\d+\.\d+)",
            txt,
            re.IGNORECASE,
        )
        if fuel_match:
            fuel = fuel or fuel_match.group(1).capitalize()
            engine = fuel_match.group(2)
            break
        if not fuel and re.search(r"(бензин|дизель|газ|гібрид|електро|метан)", txt, re.IGNORECASE):
            fuel = txt.split(",")[0].strip()

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
        image_url = src if src.startswith("http") else REONO_BASE_URL + src
        break

    is_premium = bool(card.find(string=re.compile(r"^\s*Преміум\s*$")))

    return ReonoCar(
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


def parse_catalog_page(html: str) -> tuple[list[ReonoCar], int]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    total = 0
    for pattern in _TOTAL_RES:
        match = pattern.search(page_text)
        if match:
            total = int(match.group(1).replace(" ", ""))
            break
    if not total:
        ads_match = re.search(r'"ads_count"\s*:\s*(\d+)', html)
        if ads_match:
            total = int(ads_match.group(1))

    cars: list[ReonoCar] = []
    seen_ids: set[int] = set()
    for card in soup.select("article[data-announcement-id]"):
        car = _parse_car_card(card)
        if not car or not car.car_id or car.car_id in seen_ids:
            continue
        seen_ids.add(car.car_id)
        cars.append(car)

    if cars:
        return cars, total

    # Fallback для старої DOM-структури (посилання /brand-model-ID без article.car-card).
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
        car_id = _parse_int(re.search(r"-(\d+)$", slug).group(1) if re.search(r"-(\d+)$", slug) else None)
        if not car_id or car_id in seen_ids:
            continue
        title_text = element.get_text(" ", strip=True)
        year_match = _YEAR_RE.search(title_text)
        if not year_match:
            img = element.find("img")
            alt = (img.get("alt") or "").strip() if img else ""
            year_match = _YEAR_RE.search(alt)
            if year_match:
                title_text = alt or title_text
        if not year_match:
            continue
        year = int(year_match.group())
        url = _normalize_url(element.get("href", ""))
        img = element.find("img")
        image_url = None
        if img:
            src = img.get("src") or img.get("data-src")
            if src and "no_img" not in src:
                image_url = src if str(src).startswith("http") else REONO_BASE_URL + str(src)
        words = title_text.split(str(year))[0].strip().split()
        brand = words[0] if words else None
        model = " ".join(words[1:]) if len(words) > 1 else None
        car = ReonoCar(
            title=title_text or f"{brand or ''} {model or ''} {year}".strip(),
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
            is_premium=pending_premium,
            url=url,
            image_url=image_url,
            car_id=car_id,
        )
        seen_ids.add(car_id)
        cars.append(car)
        pending_premium = False

    return cars, total
