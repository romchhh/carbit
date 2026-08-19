from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup, Tag

from app.services.car_market.constants import CAR_MARKET_BASE_URL

_BADGE_TEXTS = frozenset(
    {
        "На майданчику",
        "Базар",
        "Top",
        "TOP",
        "Продано",
        "Audi",
        "Онлайн",
        "Стоянка",
    }
)

_TRANS_PATTERNS = (
    r"Ручна\s*/\s*Механіка",
    r"Автомат",
    r"Варіатор",
    r"Робот",
    r"Типтронік",
)

_FUEL_PATTERNS = (
    r"Газ\s+пропан-бутан\s*/\s*Бензин",
    r"Газ\s+метан\s*/\s*Бензин",
    r"Гібрид\s+\(HEV\)",
    r"Електро",
    r"Дизель",
    r"Бензин",
    r"Газ",
)

_ENGINE_PATTERN = r"(\d+\.\d+)\s*(л|кВт·г)"

_DATE_RE = re.compile(
    r"\b\d{1,2}\s+"
    r"(?:серп|лип|черв|трав|квіт|бер|лют|січ|жовт|вер|лист|груд|черв)"
    r"\.?\b",
    re.IGNORECASE,
)


@dataclass
class CarMarketCar:
    title: str
    year: Optional[int]
    price_usd: Optional[int]
    mileage_km: Optional[int]
    mileage_raw: Optional[str]
    transmission: Optional[str]
    fuel: Optional[str]
    engine: Optional[str]
    location: Optional[str]
    listing_type: Optional[str]
    is_sold: bool
    is_top: bool
    date_added: Optional[str]
    url: str
    image_url: Optional[str]
    car_id: Optional[int]
    details: dict = field(default_factory=dict)


def _normalize_image_url(src: object) -> Optional[str]:
    if not src or not isinstance(src, str):
        return None
    src = src.strip()
    if not src or src.startswith("data:"):
        return None
    return src if src.startswith("http") else CAR_MARKET_BASE_URL + src


def _img_src(img: Tag) -> Optional[str]:
    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
        url = _normalize_image_url(img.get(attr))
        if url:
            return url
    srcset = img.get("srcset") or img.get("data-srcset")
    if srcset:
        first = str(srcset).split(",")[0].strip().split()[0]
        url = _normalize_image_url(first)
        if url:
            return url
    return None


def _card_container(a_tag: Tag) -> Optional[Tag]:
    """Обгортка картки (фото в сусідньому <a>, не в текстовому)."""
    node = a_tag.parent
    while node is not None and hasattr(node, "get"):
        if getattr(node, "name", None) != "div":
            node = node.parent
            continue
        classes = node.get("class") or []
        class_set = set(classes)
        if "group" in class_set and any("rounded" in c for c in classes):
            return node
        node = node.parent
    return None


def _is_car_market_image(url: str) -> bool:
    return "/uploads/cars/" in url or "/uploads/user/" in url


def _image_from_card_context(a_tag: Tag) -> Optional[str]:
    for img in a_tag.find_all("img", limit=3):
        url = _img_src(img)
        if url and _is_car_market_image(url):
            return url
    container = _card_container(a_tag)
    if container:
        for img in container.find_all("img", limit=5):
            url = _img_src(img)
            if url and _is_car_market_image(url):
                return url
    return None


def parse_catalog_page(html: str) -> tuple[list[CarMarketCar], int]:
    soup = BeautifulSoup(html, "html.parser")
    total = 0
    total_match = re.search(r"Знайдено\s+([\d\s]+)\s+авто", soup.get_text())
    if total_match:
        total = int(total_match.group(1).replace(" ", ""))

    body = soup.find("body") or soup
    cars: list[CarMarketCar] = []
    current_badges: list[str] = []
    seen_urls: set[str] = set()

    for element in body.descendants:
        if not hasattr(element, "get"):
            text = str(element).strip()
            if text in _BADGE_TEXTS:
                current_badges.append(text)
            continue

        if getattr(element, "name", None) != "a":
            continue

        href = element.get("href", "")
        if "/auto/" not in href:
            continue

        url = href if href.startswith("http") else CAR_MARKET_BASE_URL + href
        raw_text = element.get_text(" ", strip=True)
        if not raw_text or url in seen_urls:
            continue

        car = _parse_card(element, list(current_badges))
        if car:
            car.date_added = _find_date_near(element)
            cars.append(car)
            seen_urls.add(url)
        current_badges = []

    return cars, total


def _parse_card(a_tag: Tag, badges_before: list[str]) -> CarMarketCar | None:
    href = a_tag.get("href", "")
    if not href or "/auto/" not in href:
        return None

    url = href if href.startswith("http") else CAR_MARKET_BASE_URL + href
    car_id = None
    id_match = re.search(r"-(\d+)$", href)
    if id_match:
        car_id = int(id_match.group(1))

    image_url = _image_from_card_context(a_tag)

    raw = a_tag.get_text(" ", strip=True)
    year_match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", raw)
    if not year_match:
        return None

    year = int(year_match.group())
    title = _deduplicate_title(raw[: year_match.start()].strip())
    after_year = raw[year_match.end() :].strip()

    price = None
    price_match = re.search(r"([\d\s]+)\$", after_year)
    if price_match:
        price = int(price_match.group(1).replace("\xa0", "").replace(" ", ""))
        after_year = after_year[price_match.end() :].strip()

    mileage_raw = None
    mileage_km = None
    mil_match = re.search(r"([\d\s]+)\s*тис\.?\s*км", after_year)
    if mil_match:
        mileage_raw = mil_match.group(0).strip()
        num_str = mil_match.group(1).replace(" ", "").replace("\xa0", "")
        num = float(num_str)
        mileage_km = int(num) if num > 1500 else int(num * 1000)
        after_year = after_year[mil_match.end() :].strip()

    transmission, fuel, engine, location = _parse_specs(after_year)

    listing_type = None
    is_sold = False
    is_top = False
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

    return CarMarketCar(
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
        date_added=None,
        url=url,
        image_url=image_url,
        car_id=car_id,
    )


def _deduplicate_title(title: str) -> str:
    words = title.split()
    half = len(words) // 2
    if half > 0 and words[:half] == words[half:]:
        return " ".join(words[:half])
    for n in range(2, min(6, len(words))):
        prefix = " ".join(words[:n])
        rest = title[len(prefix) :].strip()
        if rest.startswith(prefix):
            return prefix
    return title


def _parse_specs(text: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    text = text.strip()
    transmission = None
    fuel = None
    engine = None
    location = None
    remaining = text

    for pat in _TRANS_PATTERNS:
        m = re.search(pat, remaining, re.IGNORECASE)
        if m:
            transmission = m.group(0).strip()
            remaining = remaining[: m.start()] + remaining[m.end() :]
            remaining = remaining.strip()
            break

    for pat in _FUEL_PATTERNS:
        m = re.search(pat, remaining, re.IGNORECASE)
        if m:
            fuel = m.group(0).strip()
            remaining = remaining[: m.start()] + remaining[m.end() :]
            remaining = remaining.strip()
            break

    m = re.search(_ENGINE_PATTERN, remaining)
    if m:
        engine = m.group(0).strip()
        remaining = remaining[: m.start()] + remaining[m.end() :]
        remaining = remaining.strip()

    remaining = re.sub(r"\s+", " ", remaining).strip()
    remaining = re.sub(r"^\d+$", "", remaining).strip()
    if remaining and len(remaining) > 1:
        location = remaining

    return transmission, fuel, engine, location


def _find_date_near(a_tag: Tag) -> Optional[str]:
    node = a_tag.next_sibling
    checks = 0
    while node and checks < 10:
        if hasattr(node, "get_text"):
            txt = node.get_text(" ", strip=True)
        else:
            txt = str(node).strip()
        m = _DATE_RE.search(txt)
        if m:
            return m.group(0)
        node = getattr(node, "next_sibling", None)
        checks += 1
    return None
