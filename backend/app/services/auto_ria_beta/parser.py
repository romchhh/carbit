"""HTML-парсер auto.ria.com (логіка з cartest4.py + JSON-шаблони SSR)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from app.services.auto_ria_beta.constants import BASE_URL

LISTING_URL_RE = re.compile(r"/uk/auto_[a-z0-9_\-]+_(\d+)\.html", re.IGNORECASE)
NEW_LISTING_URL_RE = re.compile(
    r"/uk/newauto/auto-([a-z0-9\-]+)-(\d+)\.html",
    re.IGNORECASE,
)
LISTING_ID_RAW_RE = re.compile(r"auto_[a-z0-9_\-]+_(\d+)\.html", re.IGNORECASE)
KM_EXACT_RE = re.compile(r"(\d[\d\s]*)\s*км", re.IGNORECASE)
VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
PLATE_RE = re.compile(r"\b[A-ZА-ЯІЇЄ]{2}\s?\d{4}\s?[A-ZА-ЯІЇЄ]{2}\b")
PRICE_USD_UAH_RE = re.compile(r"([\d\s]{3,})\s*\$\s*[•·]\s*([\d\s]{3,})\s*грн")
PRICE_USD_ONLY_RE = re.compile(r"([\d\s]{3,})\s*\$")
MILEAGE_RE = re.compile(r"([\d\s]+)\s*тис\.?\s*км")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")
JSON_CONTENT_RE = re.compile(r'"content"\s*:\s*"((?:\\.|[^"\\])*)"')
IMPORT_ORIGIN_RE = re.compile(r"Пригнано з\s+([^•,\n]+)", re.IGNORECASE)
LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

FUEL_WORDS = ["Електро", "Бензин", "Дизель", "Гібрид", "Газ"]
TRANS_WORDS = ["Автомат", "Механіка", "Ручна", "Типтронік", "Робот", "Варіатор"]
DRIVE_WORDS = ["Передній", "Задній", "Повний"]
BODY_WORDS = [
    "Позашляховик / Кросовер",
    "Позашляховик",
    "Кросовер",
    "Седан",
    "Хетчбек",
    "Універсал",
    "Купе",
    "Мінівен",
    "Пікап",
    "Ліфтбек",
    "Кабріолет",
    "Мікроавтобус",
    "Фургон",
]
FUEL_WITH_VOLUME_RE = re.compile(
    r"(Електро|Бензин|Дизель|Гібрид|Газ)(?:\s*,?\s*\d+[.,]?\d*\s*л\.?)?",
    re.IGNORECASE,
)
# Photo alt: «Кросовер Zeekr 001 2026 в Київ» / «BMW X5 2015 в Львові»
_PHOTO_CITY_RE = re.compile(
    r"\sв\s+([А-ЯІЇЄҐA-Z][А-ЯІЇЄҐа-яіїєґA-Za-z'\-]*(?:\s+[А-ЯІЇЄҐа-яіїєґA-Za-z'\-]+)?)\s*$"
)
_CARD_CITY_CUT_MARKERS = (
    "Доступний кредит",
    "Наші переваги",
    "В наявності.",
    "Від офіційного",
)
_CITY_DISPLAY = {
    "київ": "Київ",
    "києві": "Київ",
    "киев": "Київ",
    "киеве": "Київ",
    "львів": "Львів",
    "львові": "Львів",
    "львове": "Львів",
    "харків": "Харків",
    "харкові": "Харків",
    "одеса": "Одеса",
    "одесі": "Одеса",
    "дніпро": "Дніпро",
    "дніпрі": "Дніпро",
    "запоріжжя": "Запоріжжя",
    "запоріжжі": "Запоріжжя",
    "вінниця": "Вінниця",
    "вінниці": "Вінниця",
    "полтава": "Полтава",
    "полтаві": "Полтава",
    "черкаси": "Черкаси",
    "черкасах": "Черкаси",
    "миколаїв": "Миколаїв",
    "миколаєві": "Миколаїв",
    "херсон": "Херсон",
    "херсоні": "Херсон",
    "житомир": "Житомир",
    "житомирі": "Житомир",
    "чернігів": "Чернігів",
    "чернігові": "Чернігів",
    "суми": "Суми",
    "сумах": "Суми",
    "рівне": "Рівне",
    "рівному": "Рівне",
    "луцьк": "Луцьк",
    "луцьку": "Луцьк",
    "івано-франківськ": "Івано-Франківськ",
    "івано-франківську": "Івано-Франківськ",
    "тернопіль": "Тернопіль",
    "тернополі": "Тернопіль",
    "ужгород": "Ужгород",
    "ужгороді": "Ужгород",
    "чернівці": "Чернівці",
    "чернівцях": "Чернівці",
    "кропивницький": "Кропивницький",
    "кропивницькому": "Кропивницький",
    "хмельницький": "Хмельницький",
    "хмельницькому": "Хмельницький",
    "бровари": "Бровари",
    "броварах": "Бровари",
    "ірпінь": "Ірпінь",
    "ірпені": "Ірпінь",
    "буча": "Буча",
    "бучі": "Буча",
    "бориспіль": "Бориспіль",
    "борисполі": "Бориспіль",
    "біла церква": "Біла Церква",
    "білій церкві": "Біла Церква",
}

_USA_ORIGIN_RE = re.compile(r"сша|usa|америк|штати|copart|iaai", re.IGNORECASE)
_ACCIDENT_NONE_HINTS = (
    "немає офіційно",
    "немає офiц",
    "не виявл",
    "не зареєстр",
    "відсутн",
    "немає дтп",
    "без дтп",
)
_OPTION_SECTIONS = (
    ("descSecurityValue", "Безпека"),
    ("descComfortValue", "Комфорт"),
    ("descOpticsValue", "Оптика"),
    ("descParktronicValue", "Система допомоги при паркуванні"),
    ("descAirbagValue", "Подушка безпеки"),
)
_SALON_FIELDS = (
    ("descInteriorColorsValue", "Колір салону"),
    ("descSeatAdjustmentValue", "Регулювання сидінь салону по висоті"),
    ("descSeatVentilationValue", "Вентиляція сидінь"),
    ("descSeatHeatedValue", "Підігрів сидінь"),
    ("descMemorySeatModuleValue", "Памʼять положення сидіння"),
    ("descWindowLifterValue", "Електросклопідйомники"),
    ("descConditionerTypeValue", "Кондиціонер"),
    ("descPowerSteeringValue", "Підсилювач керма"),
    ("descSteeringWheelAdjustmentValue", "Регулювання керма"),
)


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
    is_new: bool = False


def parse_total_count(html: str) -> int:
    match = re.search(
        r'"id"\s*:\s*"sortButtonContentCount"[\s\S]{0,500}?"content"\s*:\s*"([\d\s]+)\s*пропозиц',
        html,
    )
    if match:
        digits = match.group(1).replace(" ", "").replace("\xa0", "")
        if digits.isdigit():
            return int(digits)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    counts: list[int] = []
    for item in re.findall(r"([\d\s]{1,7})\s*пропозиц", text):
        digits = item.replace(" ", "").replace("\xa0", "")
        if not digits.isdigit():
            continue
        value = int(digits)
        if value not in {10, 20, 30, 50, 100}:
            counts.append(value)
    return max(counts) if counts else 0


def parse_search_page(html: str) -> tuple[list[ScrapedCar], int]:
    total = parse_total_count(html)
    soup = BeautifulSoup(html, "html.parser")
    cars: list[ScrapedCar] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        car = _parse_search_card(anchor)
        if not car:
            continue
        key = f"n:{car.car_id}" if car.is_new else str(car.car_id)
        if key in seen:
            continue
        cars.append(car)
        seen.add(key)

    if not cars:
        for match in LISTING_ID_RAW_RE.finditer(html):
            car_id = int(match.group(1))
            key = str(car_id)
            if key in seen:
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
            seen.add(key)

    return cars, total


def _parse_search_card(anchor) -> ScrapedCar | None:
    href = anchor.get("href", "") or ""
    new_match = NEW_LISTING_URL_RE.search(href)
    used_match = LISTING_URL_RE.search(href)
    if new_match:
        slug, raw_id = new_match.group(1), new_match.group(2)
        car_id = int(raw_id)
        is_new = True
        url = href if href.startswith("http") else BASE_URL + href
        slug_parts = [part for part in slug.split("-") if part]
        brand = slug_parts[0].title() if slug_parts else None
        model = " ".join(slug_parts[1:]).upper() if len(slug_parts) > 1 else None
    elif used_match:
        car_id = int(used_match.group(1))
        is_new = False
        url = href if href.startswith("http") else BASE_URL + href
        slug = href.rstrip("/").split("/")[-1].replace(".html", "")
        parts = slug.split("_")
        brand = parts[1] if len(parts) > 1 else None
        model = "-".join(parts[2:-1]).replace("-", " ").title() if len(parts) > 3 else None
    else:
        return None

    text = anchor.get_text(" ", strip=True)

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
    else:
        km_match = KM_EXACT_RE.search(text)
        if km_match:
            mileage_km = int(km_match.group(1).replace(" ", "").replace("\xa0", ""))
        elif re.search(r"без пробігу", text, re.IGNORECASE):
            mileage_km = 0

    img = anchor.find("img")
    photo_url = None
    photo_alt = ""
    if img:
        src = img.get("src") or img.get("data-src")
        if src and str(src).startswith("http"):
            photo_url = str(src)
        photo_alt = str(img.get("alt") or "")

    details = _search_card_flags(text)
    fuel_match = FUEL_WITH_VOLUME_RE.search(text)
    fuel = fuel_match.group(0).strip() if fuel_match else next((word for word in FUEL_WORDS if word in text), None)
    body_type = next((word for word in BODY_WORDS if word in text), None)
    plate_match = PLATE_RE.search(text)
    return ScrapedCar(
        car_id=car_id,
        url=url,
        brand=brand,
        model=model,
        year=year,
        price_usd=price_usd,
        price_uah=price_uah,
        mileage_km=mileage_km,
        city=_parse_search_card_city(text, photo_alt=photo_alt),
        fuel=fuel,
        transmission=next((word for word in TRANS_WORDS if word in text), None),
        drive=next((word for word in DRIVE_WORDS if word in text), None),
        body_type=body_type,
        plate=plate_match.group(0) if plate_match else None,
        is_dealer="Перевірений дилер" in text or "Офіційний дилер" in text,
        photo_url=photo_url,
        details=details,
        is_new=is_new,
    )


def _normalize_card_city(raw: str | None) -> str | None:
    key = " ".join((raw or "").strip().lower().split())
    if not key:
        return None
    mapped = _CITY_DISPLAY.get(key)
    if mapped:
        return mapped
    if re.fullmatch(r"[а-яёіїєґa-z'\-]+(?:\s+[а-яёіїєґa-z'\-]+)?", key):
        return raw.strip()
    return None


def _parse_search_card_city(text: str, *, photo_alt: str = "") -> str | None:
    alt_match = _PHOTO_CITY_RE.search((photo_alt or "").strip())
    if alt_match:
        city = _normalize_card_city(alt_match.group(1))
        if city:
            return city

    spec = text or ""
    for marker in _CARD_CITY_CUT_MARKERS:
        idx = spec.find(marker)
        if idx != -1:
            spec = spec[:idx]
            break
    spec = spec[:500]
    spec_key = spec.lower()
    best_pos: int | None = None
    best_name: str | None = None
    best_len = 0
    for locative, nominative in _CITY_DISPLAY.items():
        if len(locative) < 4:
            continue
        match = re.search(
            rf"(?<![a-zа-яёіїєґ]){re.escape(locative)}(?![a-zа-яёіїєґ])",
            spec_key,
        )
        if not match:
            continue
        pos = match.start()
        if (
            best_pos is None
            or pos < best_pos
            or (pos == best_pos and len(locative) > best_len)
        ):
            best_pos = pos
            best_name = nominative
            best_len = len(locative)
    return best_name


def _search_card_flags(text: str) -> dict[str, Any]:
    details: dict[str, Any] = {}
    if "Перевірений VIN" in text:
        details["vin_checked"] = True
    if "Був у ДТП" in text or "Був в ДТП" in text:
        details["had_accident"] = True
    origin_match = IMPORT_ORIGIN_RE.search(text)
    if origin_match:
        origin = origin_match.group(1).strip()
        details["import_origin"] = origin
        details["usa_import"] = is_usa_import_text(origin)
    elif "з США" in text or "зі США" in text:
        details["import_origin"] = "США"
        details["usa_import"] = True
    if re.search(r"нерозмитнен", text, re.IGNORECASE):
        details["not_customs"] = True
    return details


def is_usa_import_text(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return bool(_USA_ORIGIN_RE.search(text))


def _unescape_json_string(value: str) -> str:
    try:
        parsed = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        parsed = value.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/")
    if not isinstance(parsed, str):
        return str(parsed)
    return parsed.replace("\xa0", " ").replace("\u00a0", " ")


def _contents_near_id(html: str, template_id: str, window: int = 3500) -> list[str]:
    found: list[str] = []
    for match in re.finditer(rf'"id"\s*:\s*"{re.escape(template_id)}"', html):
        chunk = html[match.end() : match.end() + window]
        if re.match(r'\s*,\s*"isHide"\s*:\s*true', chunk):
            continue
        for content_match in JSON_CONTENT_RE.finditer(chunk):
            text = _unescape_json_string(content_match.group(1)).strip()
            if not text or text.startswith("{") or len(text) > 2500:
                continue
            if text not in found:
                found.append(text)
            if len(found) >= 8:
                return found
    return found


def _first_content(html: str, template_id: str, window: int = 3500) -> str | None:
    contents = _contents_near_id(html, template_id, window=window)
    return contents[0] if contents else None


def _badge_visible(html: str, badge_id: str) -> bool:
    return bool(
        re.search(
            rf'"id"\s*:\s*"{re.escape(badge_id)}"\s*,\s*"isHide"\s*:\s*false',
            html,
            re.IGNORECASE,
        )
    )


def _split_bullets(text: str | None) -> list[str]:
    if not text:
        return []
    parts = re.split(r"\s*•\s*", text.replace("\xa0", " "))
    return [part.strip(" \t-") for part in parts if part.strip(" \t-")]


def _clean_vin(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^A-HJ-NPR-Z0-9]", "", value.upper())
    return compact if VIN_RE.fullmatch(compact) else None


def _accident_from_vin_check(text: str | None) -> bool | None:
    if not text:
        return None
    lowered = text.lower()
    if any(hint in lowered for hint in _ACCIDENT_NONE_HINTS):
        return False
    if "дтп" in lowered or "accident" in lowered:
        return True
    return None


def _label_value(lines: list[str], label: str) -> str | None:
    try:
        idx = lines.index(label)
    except ValueError:
        return None
    for nxt in lines[idx + 1 : idx + 3]:
        if nxt and nxt != label:
            return nxt
    return None


def _iter_ld_json(html: str):
    for raw in LD_JSON_RE.findall(html):
        try:
            yield json.loads(raw.strip())
        except (json.JSONDecodeError, TypeError):
            continue


def _apply_json_ld(html: str, car: ScrapedCar, details: dict[str, Any]) -> None:
    for payload in _iter_ld_json(html):
        if not isinstance(payload, dict) or payload.get("@type") != "Vehicle":
            continue
        name = payload.get("name")
        if isinstance(name, str) and name.strip() and not car.brand:
            bits = name.strip().split()
            if bits:
                car.brand = bits[0]
        brand = payload.get("brand")
        if isinstance(brand, dict) and isinstance(brand.get("name"), str):
            car.brand = car.brand or brand["name"]
        elif isinstance(brand, str):
            car.brand = car.brand or brand
        model = payload.get("model")
        if isinstance(model, str) and model.strip():
            car.model = model.strip()
        vin = _clean_vin(str(payload.get("vehicleIdentificationNumber") or ""))
        if vin:
            car.vin = vin
        produced = payload.get("productionDate") or payload.get("modelDate")
        if produced:
            year_match = YEAR_RE.search(str(produced))
            if year_match:
                car.year = int(year_match.group())
        color = payload.get("color")
        if isinstance(color, str) and color.strip():
            car.color = color.strip()
        fuel = payload.get("fuelType")
        if isinstance(fuel, str) and fuel.strip():
            car.fuel = fuel.strip()
        transmission = payload.get("vehicleTransmission")
        if isinstance(transmission, str) and transmission.strip():
            car.transmission = transmission.strip()
        description = payload.get("description")
        if isinstance(description, str) and description.strip():
            car.description = description.strip()[:2000]
        body = payload.get("bodyType")
        if isinstance(body, str) and body.strip() and body.strip() not in {"Легкові", "Легковые"}:
            car.body_type = body.strip()
        doors = payload.get("numberOfDoors")
        if doors is not None:
            try:
                details["doors"] = int(doors)
            except (TypeError, ValueError):
                pass
        mileage = payload.get("mileageFromOdometer")
        if isinstance(mileage, dict) and mileage.get("value") is not None:
            try:
                car.mileage_km = int(float(mileage["value"]))
            except (TypeError, ValueError):
                pass
        offers = payload.get("offers")
        if isinstance(offers, dict):
            currency = str(offers.get("priceCurrency") or "").upper()
            try:
                price = int(float(offers.get("price")))
            except (TypeError, ValueError):
                price = None
            if price:
                if currency == "USD":
                    car.price_usd = car.price_usd or price
                elif currency == "UAH":
                    car.price_uah = car.price_uah or price
                else:
                    car.price_usd = car.price_usd or price
        break


def _apply_badges(html: str, car: ScrapedCar, details: dict[str, Any]) -> None:
    plate = _first_content(html, "badgesPlateNumber", window=800)
    if plate:
        car.plate = plate
        details["plate"] = plate

    for badge_id in ("badgesVin", "badgesVervin"):
        vin = _clean_vin(_first_content(html, badge_id, window=2500))
        if vin:
            car.vin = vin
            details["vin_checked"] = True
            break

    origin = _first_content(html, "badgesOrderFrom", window=800)
    if origin and _badge_visible(html, "badgesOrderFrom"):
        details["import_origin"] = origin
        details["usa_import"] = is_usa_import_text(origin)
        details["display"]["Пригнано з"] = origin

    if _badge_visible(html, "badgesDamaged"):
        details["had_accident"] = True
        damaged_text = _first_content(html, "badgesDamaged", window=800)
        if damaged_text:
            details["display"]["ДТП"] = damaged_text

    if _badge_visible(html, "badgesFirstRegistration"):
        details["display"]["Перша реєстрація"] = (
            _first_content(html, "badgesFirstRegistration", window=600) or "Так"
        )


def _apply_spec_templates(html: str, car: ScrapedCar, details: dict[str, Any]) -> None:
    engine = _first_content(html, "descEngineEngine")
    if engine:
        car.fuel = engine
        details["engine"] = engine
    transmission = _first_content(html, "descTransmissionTransmission")
    if transmission:
        car.transmission = transmission
    drive = _first_content(html, "descDriveTypeDriveType")
    if drive:
        car.drive = drive
    color = _first_content(html, "descColorColor")
    if color:
        car.color = color

    characteristics = _first_content(html, "descCharacteristicsValue") or _first_content(
        html, "descCharacteristics"
    )
    if characteristics:
        bits = _split_bullets(characteristics)
        if bits:
            car.body_type = car.body_type or bits[0]
            details["body_type"] = bits[0]
        doors_match = re.search(r"(\d+)\s*двер", characteristics)
        seats_match = re.search(r"(\d+)\s*місц", characteristics)
        if doors_match:
            details["doors"] = int(doors_match.group(1))
        if seats_match:
            details["seats"] = int(seats_match.group(1))
        details["display"]["Кузов"] = characteristics

    generation = _first_content(html, "descGenerationBaseValue")
    if generation:
        details["generation_trim"] = generation
        details["display"]["Покоління, комплектація, модифікація"] = generation

    tech_state = _first_content(html, "descTechStateText")
    if tech_state:
        details["technical_condition"] = tech_state
        details["display"]["Технічний стан"] = tech_state
    tech_note = _first_content(html, "descTechStateValue")
    if tech_note:
        details["display"]["Готовність до перевірки"] = tech_note

    condition = _first_content(html, "descStateValue")
    if condition:
        flags = _split_bullets(condition)
        details["condition_list"] = flags or [condition]
        details["display"]["Стан"] = condition

    description = _first_content(html, "descDescription", window=8000)
    if description:
        car.description = description.strip()[:2000]


def _apply_options(html: str, details: dict[str, Any]) -> None:
    options: dict[str, Any] = {}
    for template_id, label in _OPTION_SECTIONS:
        value = _first_content(html, template_id, window=2500)
        if value:
            options[label] = _split_bullets(value) or [value]
            details["display"][label] = value
    salon: dict[str, str] = {}
    for template_id, label in _SALON_FIELDS:
        value = _first_content(html, template_id)
        if value:
            salon[label] = value
            details["display"][label] = value
    if salon:
        options["Салон"] = salon
    if options:
        details["options"] = options


def _apply_electric(html: str, details: dict[str, Any]) -> None:
    electric: dict[str, Any] = {}
    mapping = (
        ("elDescAccumCapacityValue", "battery_capacity", "Ємність акумулятора"),
        ("elDescStateOfHelthValue", "battery_health_soh", "Здоровʼя акумулятора (SOH)"),
        ("elDescBatteryStatusValue", "battery_state", "Стан акумулятора"),
        ("elDescElectroDistanceRangeValue", "range_km_100pct", "Запас ходу, км/100%"),
        ("elDescEnergyEfficiencyValue", "energy_efficiency", "Енергоефективність"),
        ("elDescElectroEnginePowerValue", "motor_power", "Потужність двигуна"),
    )
    for template_id, key, label in mapping:
        value = _first_content(html, template_id)
        if value:
            electric[key] = value
            details["display"][label] = value
    connectors = []
    for template_id in ("elDescChargerSocketsshow0", "elDescChargerSocketsshow1"):
        value = _first_content(html, template_id)
        if value and value.strip() not in connectors:
            connectors.append(value.strip())
    if connectors:
        electric["charging_connector"] = connectors
        details["display"]["Зарядний розʼєм"] = " • ".join(connectors)
    if electric:
        details["electric"] = electric


def _apply_vin_check(html: str, details: dict[str, Any]) -> None:
    vin_check: dict[str, Any] = {}
    pairs = (
        ("verifyingsNaisName0", "verifyingsNaisText00"),
        ("verifyingsNaisName1", "verifyingsNaisText10"),
        ("verifyingsProvenRaceName0", "verifyingsProvenRaceText00"),
        ("verifyingsProvenRaceName1", "verifyingsProvenRaceText10"),
        ("verifyingsProvenDamageName0", "verifyingsProvenDamageText00"),
        ("verifyingsProvenDamageName1", "verifyingsProvenDamageText10"),
    )
    label_to_key = {
        "тип обтяження": "pledge_type",
        "обмеження відчуження": "pledge_restriction",
        "останній перевірений пробіг": "last_checked_mileage",
        "пробіг від продавця": "seller_stated_mileage",
        "дтп": "accidents_registered",
        "страхові випадки в україні": "insurance_cases",
    }
    for name_id, value_id in pairs:
        label = _first_content(html, name_id, window=600)
        value = _first_content(html, value_id, window=800)
        if not label or not value:
            continue
        details["display"][label] = value
        key = label_to_key.get(label.strip().lower())
        if key:
            vin_check[key] = value
    if _first_content(html, "verifyingsVertitle"):
        details["vin_checked"] = True
    accidents = vin_check.get("accidents_registered")
    parsed_had = _accident_from_vin_check(accidents if isinstance(accidents, str) else None)
    if parsed_had is not None and details.get("had_accident") is not True:
        details["had_accident"] = parsed_had
    if vin_check:
        details["vin_check"] = vin_check


def _apply_seller(html: str, car: ScrapedCar, details: dict[str, Any]) -> None:
    seller: dict[str, Any] = {}
    name = _first_content(html, "sellerInfoUserName", window=800)
    if name and name not in {"Продавець", "Подзвонити"}:
        seller["name"] = name
        car.seller_name = name
    years = _first_content(html, "sellerInfoWorkWithText", window=800)
    if years:
        seller["years_on_platform"] = years.strip()
    dia = _first_content(html, "sellerInfoDia", window=800)
    if dia:
        seller["diia"] = dia
        if "дію" in dia.lower() or "diia" in dia.lower():
            seller["verified_via_diia"] = True
    if seller:
        details["seller"] = seller
        if seller.get("diia"):
            details["display"]["Продавець"] = seller.get("name") or ""
            details["display"]["Підтвердження"] = seller["diia"]


def _apply_text_fallbacks(full_text: str, lines: list[str], car: ScrapedCar, details: dict[str, Any]) -> None:
    if not car.vin:
        vin_match = VIN_RE.search(full_text)
        if vin_match:
            car.vin = vin_match.group(0)
    if not car.plate:
        plate_match = PLATE_RE.search(full_text)
        if plate_match:
            car.plate = plate_match.group(0)

    price_match = PRICE_USD_UAH_RE.search(full_text)
    if price_match:
        car.price_usd = int(price_match.group(1).replace(" ", "").replace("\xa0", ""))
        car.price_uah = int(price_match.group(2).replace(" ", "").replace("\xa0", ""))

    if car.mileage_km is None:
        mileage_match = MILEAGE_RE.search(full_text)
        if mileage_match:
            car.mileage_km = int(float(mileage_match.group(1).replace(" ", "").replace("\xa0", "")) * 1000)

    car.fuel = car.fuel or _label_value(lines, "Двигун")
    car.transmission = car.transmission or _label_value(lines, "Коробка передач")
    car.drive = car.drive or _label_value(lines, "Привід")
    car.color = car.color or _label_value(lines, "Колір")

    location_match = re.search(r"UA,\s*([^,]+),\s*([^,]+),\s*\d{5}", full_text)
    if location_match:
        car.city = location_match.group(2).strip()
        details["region"] = location_match.group(1).strip()
        details["display"]["Область"] = details["region"]

    if not car.body_type:
        body_match = re.search(
            r"(Седан|Хетчбек|Універсал|Купе|Мінівен|Пікап|Ліфтбек|"
            r"Позашляховик\s*/\s*Кросовер|Кабріолет)",
            full_text,
        )
        if body_match:
            car.body_type = body_match.group(1)

    car.is_dealer = ("Перевірений дилер" in full_text) or car.is_dealer

    if "Підтверджено через Дію" in full_text:
        seller = details.setdefault("seller", {})
        seller["verified_via_diia"] = True

    owners_match = re.search(r"(\d+)\s*власник", full_text)
    if owners_match:
        details.setdefault("vin_check", {})["owners_count"] = int(owners_match.group(1))
        details["display"]["Власників"] = owners_match.group(1)

    if "Відсутній у розшуку" in full_text:
        details.setdefault("vin_check", {})["wanted_status"] = "не в розшуку"
        details["display"]["Розшук"] = "Відсутній у розшуку"

    if re.search(r"нерозмитнен", full_text, re.IGNORECASE):
        details["not_customs"] = True
        details["display"]["Розмитнення"] = "Нерозмитнений"

    views_match = re.search(r"Переглядів авто\s*([\d\s]+)", full_text)
    if views_match:
        car.views = int(views_match.group(1).replace(" ", "").replace("\xa0", ""))
    created_match = re.search(r"Оголошення створене\s*(\d{2}\.\d{2}\.\d{4})", full_text)
    if created_match:
        car.posted = created_match.group(1)

    if not car.description:
        description_match = re.search(
            r"Опис від продавця\s*(.+?)(?:Позашляховик|Седан|Хетчбек|Універсал|"
            r"Купе|Мінівен|Покоління|$)",
            full_text,
        )
        if description_match:
            car.description = description_match.group(1).strip()[:2000]


def parse_listing_details(html: str, car: ScrapedCar) -> dict[str, Any]:
    raw_html = html.replace("\\/", "/")
    soup = BeautifulSoup(raw_html, "html.parser")
    details: dict[str, Any] = dict(car.details or {})
    details.setdefault("display", {})
    full_text = soup.get_text(" ", strip=True)
    lines = [line.strip() for line in soup.get_text("\n", strip=True).split("\n") if line.strip()]

    _apply_json_ld(raw_html, car, details)
    _apply_badges(raw_html, car, details)
    _apply_spec_templates(raw_html, car, details)
    _apply_options(raw_html, details)
    _apply_electric(raw_html, details)
    _apply_vin_check(raw_html, details)
    _apply_seller(raw_html, car, details)
    _apply_text_fallbacks(full_text, lines, car, details)

    photos = _extract_photos(raw_html, soup)
    if photos:
        car.photos = photos
        car.photo_url = car.photo_url or photos[0]
        details["photos"] = photos
        details["photos_count"] = len(photos)

    display = details.get("display")
    if isinstance(display, dict):
        details["display"] = {key: value for key, value in display.items() if value not in (None, "", [], {})}

    cleaned = {key: value for key, value in details.items() if value not in (None, {}, [], "")}
    car.details = cleaned
    return cleaned


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
