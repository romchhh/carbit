from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.services.lubeavto.constants import LUBEAVTO_BASE_URL

FUEL_WORDS = ("Бензин", "Дизель", "Гібрид", "Електро", "Газ")
TRANS_WORDS = ("Автомат", "Механіка", "Робот", "Варіатор", "Типтронік")
DRIVE_WORDS = ("Передній", "Задній", "Повний")

VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
CARD_ID_RE = re.compile(r"^/store/(?:instore|instoreusers|auction)/(\d+)$")


@dataclass
class LubeAvtoCar:
    title: str
    brand: Optional[str]
    model: Optional[str]
    year: Optional[int]
    price_usd: Optional[int]
    mileage_km: Optional[int]
    mileage_raw: Optional[str]
    fuel: Optional[str]
    engine: Optional[str]
    transmission: Optional[str]
    drive: Optional[str]
    vin: Optional[str]
    badge: Optional[str]
    url: str
    image_url: Optional[str]
    car_id: Optional[int]
    catalog: str = "instore"
    details: dict = field(default_factory=dict)


def _normalize_image_url(src: object) -> Optional[str]:
    if not src or not isinstance(src, str):
        return None
    src = src.strip()
    if not src or src.startswith("data:"):
        return None
    return src if src.startswith("http") else urljoin(LUBEAVTO_BASE_URL, src)


def _find_card_container(title_a: Tag) -> Tag:
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
            return node if node is not title_a else parent
        node = parent
    return node


def _parse_card(title_a: Tag, container: Tag, *, catalog: str) -> Optional[LubeAvtoCar]:
    href = title_a.get("href", "")
    match = CARD_ID_RE.match(href)
    if not match:
        return None

    car_id = int(match.group(1))
    url = href if href.startswith("http") else urljoin(LUBEAVTO_BASE_URL, href)

    h4 = title_a.find("h4") or title_a
    title = h4.get_text(" ", strip=True)

    year_match = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", title)
    year = int(year_match.group()) if year_match else None
    name_part = title[: year_match.start()].strip() if year_match else title
    brand = name_part.split()[0] if name_part else None
    model = " ".join(name_part.split()[1:]) if len(name_part.split()) > 1 else None

    image_url = None
    for img in (title_a.find("img"), container.find("img")):
        if img is None:
            continue
        for attr in ("src", "data-src"):
            image_url = _normalize_image_url(img.get(attr))
            if image_url:
                break
        if image_url:
            break

    full_text = container.get_text(" ", strip=True)
    vin_match = VIN_RE.search(full_text)
    vin = vin_match.group(0) if vin_match else None

    badge = None
    if vin_match:
        pre = full_text[: vin_match.start()].strip()
        if pre:
            badge = pre.split(" ")[-1]

    if year is None:
        year_match2 = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", full_text)
        if year_match2:
            year = int(year_match2.group())

    price = None
    price_text = full_text[vin_match.end() :] if vin_match else full_text
    price_match = re.search(r"(\d{1,3}(?:\s\d{3})+)\s*\$", price_text)
    if not price_match:
        price_match = re.search(r"(\d[\d\s]{1,8}?)\s*\$", price_text)
    if price_match:
        price = int(price_match.group(1).replace("\xa0", "").replace(" ", ""))

    mileage_raw = None
    mileage_km = None
    mil_match = re.search(r"([\d\s]+)\s*тис\.?\s*км", full_text)
    if mil_match:
        mileage_raw = mil_match.group(0).strip()
        num = float(mil_match.group(1).replace(" ", "").replace("\xa0", ""))
        mileage_km = int(num * 1000) if num < 1500 else int(num)

    fuel = next((word for word in FUEL_WORDS if word in full_text), None)
    transmission = next((word for word in TRANS_WORDS if word in full_text), None)
    drive = next((word for word in DRIVE_WORDS if word in full_text), None)

    engine = None
    eng_match = re.search(r"(\d+\.\d+)\s*(л|kWh|кВт·г)", full_text)
    if eng_match:
        engine = eng_match.group(0).strip()

    return LubeAvtoCar(
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
        catalog=catalog,
    )


def parse_catalog_page(html: str, *, catalog: str = "instore") -> tuple[list[LubeAvtoCar], int]:
    soup = BeautifulSoup(html, "html.parser")
    total = 0
    total_match = re.search(r"Знайдено\s+([\d\s]+)\s+результат", soup.get_text())
    if total_match:
        total = int(total_match.group(1).replace(" ", ""))

    cars: list[LubeAvtoCar] = []
    seen_ids: set[int] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        match = CARD_ID_RE.match(href)
        if not match or not anchor.find("h4"):
            continue

        car_id = int(match.group(1))
        if car_id in seen_ids:
            continue

        container = _find_card_container(anchor)
        car = _parse_card(anchor, container, catalog=catalog)
        if car:
            cars.append(car)
            seen_ids.add(car_id)

    if not total:
        total = len(cars)
    return cars, total
