"""Розпізнавання голосового/текстового запиту пошуку авто через OpenAI."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.search.fe_catalog import load_fe_brand_models, fe_brand_slug_to_label, unique_model_token_owner
from app.services.olx.brand_slugs import OLX_TEXT_BRAND_VARIANTS, resolve_olx_brand_slug
from app.services.search.region_cities import cities_for_region
from app.core.text import norm_text

logger = logging.getLogger(__name__)

FUEL_OPTIONS = [
    "Бензин",
    "Дизель",
    "Електро",
    "Газ",
    "Газ пропан+бензин",
    "Газ метан+бензин",
    "Гібрид",
]
TRANSMISSION_OPTIONS = [
    "Механіка",
    "Автомат",
    "Типтронік",
    "Робот",
    "Варіатор",
    "Редуктор",
]
BODY_TYPE_OPTIONS = [
    "Седан",
    "Універсал",
    "Хетчбек",
    "Купе",
    "Мінівен",
    "Позашляховик",
    "Кросовер",
    "Пікап",
    "Ліфтбек",
]
DRIVE_OPTIONS = ["Передній", "Задній", "Повний"]
COLOR_OPTIONS = [
    "Білий",
    "Чорний",
    "Сірий",
    "Срібний",
    "Синій",
    "Червоний",
    "Зелений",
    "Жовтий",
    "Помаранчевий",
    "Коричневий",
    "Бежевий",
    "Фіолетовий",
]
REGION_OPTIONS = [
    "Вся Україна",
    "м. Київ",
    "Київська область",
    "Вінницька область",
    "Волинська область",
    "Дніпропетровська область",
    "Донецька область",
    "Житомирська область",
    "Закарпатська область",
    "Запорізька область",
    "Івано-Франківська область",
    "Кіровоградська область",
    "Луганська область",
    "Львівська область",
    "Миколаївська область",
    "Одеська область",
    "Полтавська область",
    "Рівненська область",
    "Сумська область",
    "Тернопільська область",
    "Харківська область",
    "Херсонська область",
    "Хмельницька область",
    "Черкаська область",
    "Чернівецька область",
    "Чернігівська область",
]
SOURCE_OPTIONS = ["AUTO.RIA", "OLX", "Telegram"]
SORT_OPTIONS = ["newest", "price_asc", "price_desc", "year_desc", "mileage_asc"]

SYSTEM_PROMPT = f"""Ти — асистент пошуку авто на Carbit (Україна). Користувач диктує або пише, що шукати.
Розбери запит у структуровані фільтри. Відповідай ТІЛЬКИ валідним JSON.

Правила:
- Якщо запит не про пошук авто, зовсім незрозумілий або порожній — understood=false, message українською («Не зрозумів…» + що саме неясно).
- Якщо зрозуміло хоча б марку, модель, ціну, рік, регіон або інший параметр — understood=true.
- brand і model — точні назви з каталогу (латиниця для марок: Toyota, BMW, Volkswagen тощо).
- Якщо користучач назвав марку українською/російською (тойота, бмв, мерседес) — все одно заповни brand латиницею з каталогу.
- Ніколи не пропускай brand, якщо в запиті є назва марки — навіть якщо є ще ціна, рік чи регіон.
- category: all | used | new | import (вживане/нове/під пригон).
- currency: USD | UAH | EUR (за замовчуванням USD, якщо сказали «гривень/грн» — UAH, «євро» — EUR).
- price_from/price_to, year_from/year_to — числа.
- mileage_from/mileage_to — пробіг у тисячах км (напр. «до 100 тисяч» → mileage_to=100).
- fuels, transmissions, drive_types, body_types, colors, sources — масиви з дозволених значень.
- region — одне з дозволених (м. Київ, Львівська область тощо). Заповнюй лише якщо користувач явно назвав місто чи область; інакше null — не підставляй Київ чи інший регіон за замовчуванням.
- seller_filter: private | dealer | null; accident: none | had | null.
- zero_mileage, bargain, vin_verified, metallic — boolean.
- owners_max: 1 | 2 | 3 | 4 | null (4 = 4+ власників).
- in_credit, usa_import, not_customs: show | hide | null.
- Невказані поля — null або [] (не вигадуй).
- Числа: «15 тисяч» / «15к» → 15000; «до двадцяти» з контекстом ціни → 20000; «від 2018» → year_from=2018.
- «автомат/механіка/дизель/бензин/електро/кросовер/седан» — у відповідні масиви fuels/transmissions/body_types.
- message — одне речення-резюме українською: що саме зрозумів (марка, модель, бюджет, рік, регіон).
- Якщо користувач назвав бюджет («у мене є 15 тисяч доларів») і роки без марки — це пошук по всьому ринку: brand=null, price_to=бюджет.
- «найди машину / лучшие варианты / найкращі варіанти» без марки — теж пошук по ринку в межах бюджету та років.

Приклади:
- «Тойота Камry до 20 тисяч доларів від 2018» → brand=Toyota, model=Camry, price_to=20000, currency=USD, year_from=2018
- «БМВ ікс п'ять дизель автомат Львів» → brand=BMW, model=X5, fuels=[Дизель], transmissions=[Автомат], region=Львівська область
- «Volkswagen Passat до 15к гривень» → brand=Volkswagen, model=Passat, price_to=15000, currency=UAH
- «У мене є 15 тисяч доларів, знайди авто 2020-2022, найкращі варіанти» → brand=null, price_to=15000, currency=USD, year_from=2020, year_to=2022

Дозволені значення:
fuels: {json.dumps(FUEL_OPTIONS, ensure_ascii=False)}
transmissions: {json.dumps(TRANSMISSION_OPTIONS, ensure_ascii=False)}
body_types: {json.dumps(BODY_TYPE_OPTIONS, ensure_ascii=False)}
drive_types: {json.dumps(DRIVE_OPTIONS, ensure_ascii=False)}
colors: {json.dumps(COLOR_OPTIONS, ensure_ascii=False)}
sources: {json.dumps(SOURCE_OPTIONS, ensure_ascii=False)}
regions: {json.dumps(REGION_OPTIONS, ensure_ascii=False)}

Формат відповіді:
{{
  "understood": boolean,
  "message": "коротке резюме українською або пояснення чому не зрозумів",
  "filters": {{
    "brand": string|null,
    "model": string|null,
    "category": "all"|"used"|"new"|"import"|null,
    "region": string|null,
    "year_from": number|null,
    "year_to": number|null,
    "price_from": number|null,
    "price_to": number|null,
    "currency": "USD"|"UAH"|"EUR"|null,
    "mileage_from": number|null,
    "mileage_to": number|null,
    "fuels": string[],
    "transmissions": string[],
    "drive_types": string[],
    "body_types": string[],
    "colors": string[],
    "sources": string[],
    "engine_volume_from": number|null,
    "engine_volume_to": number|null,
    "power_from": number|null,
    "power_to": number|null,
    "seller_filter": "private"|"dealer"|null,
    "accident": "none"|"had"|null,
    "zero_mileage": boolean|null,
    "bargain": boolean|null,
    "vin_verified": boolean|null,
    "owners_max": number|null,
    "in_credit": "show"|"hide"|null,
    "usa_import": "show"|"hide"|null,
    "not_customs": "show"|"hide"|null,
    "metallic": boolean|null
  }}
}}"""


def _client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не налаштовано")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _pick_allowed(values: list[str] | None, allowed: list[str]) -> list[str]:
    if not values:
        return []
    allowed_set = set(allowed)
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text in allowed_set and text not in out:
            out.append(text)
    return out


def _resolve_brand_model(brand: str | None, model: str | None) -> tuple[str | None, str | None]:
    b = str(brand or "").strip()
    m = str(model or "").strip()
    if not b and not m:
        return None, None

    catalog = load_fe_brand_models()
    brand_by_lower = {name.lower(): name for name in catalog}

    if b:
        b = brand_by_lower.get(b.lower(), b)
        if b not in catalog:
            slug = resolve_olx_brand_slug(b)
            b = fe_brand_slug_to_label().get(slug, b if b in catalog else "")

    if m and not b:
        token = norm_text(m)
        owner_slug = unique_model_token_owner().get(token)
        if owner_slug:
            b = fe_brand_slug_to_label().get(owner_slug, "")

    if b and b in catalog:
        models = catalog[b]
        model_by_lower = {name.lower(): name for name in models}
        if m:
            m = model_by_lower.get(m.lower(), m)
            if m not in models:
                compact = norm_text(m)
                for candidate in models:
                    if norm_text(candidate) == compact:
                        m = candidate
                        break
        return b, (m if m in models else (m or None))

    return (b or None), (m or None)


def _text_contains_token(haystack: str, token: str) -> bool:
    if not haystack or not token:
        return False
    pattern = rf"(?<![a-z0-9а-яёіїє]){re.escape(token)}(?![a-z0-9а-яёіїє])"
    return re.search(pattern, haystack, flags=re.IGNORECASE) is not None


def _infer_brand_from_transcript(text: str) -> str | None:
    """Якщо GPT пропустив марку — шукаємо в тексті (тойота, бмв, …)."""
    haystack = norm_text(text)
    if not haystack:
        return None

    catalog = load_fe_brand_models()
    labels = fe_brand_slug_to_label()
    best_brand: str | None = None
    best_len = 0

    for slug, variants in OLX_TEXT_BRAND_VARIANTS.items():
        brand = labels.get(slug)
        if not brand or brand not in catalog:
            continue
        for variant in variants:
            token = norm_text(variant)
            if len(token) < 2:
                continue
            if _text_contains_token(haystack, token) and len(token) > best_len:
                best_brand = brand
                best_len = len(token)

    for brand in catalog:
        token = norm_text(brand)
        if len(token) < 2:
            continue
        if _text_contains_token(haystack, token) and len(token) > best_len:
            best_brand = brand
            best_len = len(token)

    return best_brand


def _infer_model_from_transcript(text: str, brand: str) -> str | None:
    catalog = load_fe_brand_models()
    models = catalog.get(brand) or []
    if not models:
        return None

    haystack = norm_text(text)
    best_model: str | None = None
    best_len = 0

    for model in models:
        token = norm_text(model)
        if len(token) < 2:
            continue
        if _text_contains_token(haystack, token) and len(token) > best_len:
            best_model = model
            best_len = len(token)

    return best_model


def _detect_currency_in_text(text: str) -> str | None:
    lower = norm_text(text)
    if any(token in lower for token in ("грн", "грив", "uah", "гривень", "гривні")):
        return "UAH"
    if any(token in lower for token in ("євро", "eur", "€")):
        return "EUR"
    if any(token in lower for token in ("долар", "долл", "usd", "$", "бакс")):
        return "USD"
    return None


def _parse_amount(value: str, *, thousands: bool = False) -> int | None:
    cleaned = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        num = float(cleaned)
    except ValueError:
        return None
    if num <= 0:
        return None
    return int(num * 1000) if thousands else int(num)


def _looks_like_year(num: int) -> bool:
    return 1950 <= num <= 2030


def _infer_price_from_transcript(text: str) -> tuple[int | None, int | None, str | None]:
    haystack = norm_text(text)
    currency = _detect_currency_in_text(haystack)
    price_from: int | None = None
    price_to: int | None = None

    patterns_to = [
        r"(?:у мене є|у меня есть|бюджет|мій бюджет|мой бюджет|є у мене|есть у меня)\s*(\d[\d\s.,]*)\s*(?:тисяч|тис|тысяч|тыс|k|к)\b",
        r"(?:у мене є|у меня есть|бюджет)\s*(\d[\d\s.,]+)\s*(?:долар|долл|usd|\$|бакс|грн|грив|uah|€|eur)",
        r"(?:до|максимум|max)\s*(\d[\d\s.,]*)\s*(?:тисяч|тис|тысяч|тыс|k|к)\b",
        r"(?:до|максимум|max)\s*(\d[\d\s.,]+)\s*(?:грн|грив|uah|usd|\$|€|eur|дол|долл)",
        r"(\d[\d\s.,]+)\s*(?:тисяч|тис|тысяч|тыс|k|к)\s*(?:грн|грив|uah|usd|\$|€|eur|дол|долл)?",
        r"(?:до|максимум|max)\s*(\d[\d\s.,]+)\b",
    ]
    patterns_from = [
        r"(?:від|мінімум|min|от)\s*(\d[\d\s.,]*)\s*(?:тисяч|тис|тысяч|тыс|k|к)\b",
        r"(?:від|мінімум|min|от)\s*(\d[\d\s.,]+)\s*(?:грн|грив|uah|usd|\$|€|eur|дол|долл)",
        r"(?:від|мінімум|min|от)\s*(\d[\d\s.,]+)\b",
    ]

    for pattern in patterns_to:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1)
        thousands = bool(
            re.search(r"(?:тисяч|тис|тысяч|тыс|k|к)\b", match.group(0), flags=re.IGNORECASE)
        )
        parsed = _parse_amount(raw, thousands=thousands or (not thousands and float(raw.replace(",", ".")) < 500))
        if parsed and not _looks_like_year(parsed):
            price_to = parsed
            break

    for pattern in patterns_from:
        match = re.search(pattern, haystack, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1)
        thousands = bool(
            re.search(r"(?:тисяч|тис|тысяч|тыс|k|к)\b", match.group(0), flags=re.IGNORECASE)
        )
        parsed = _parse_amount(raw, thousands=thousands or (not thousands and float(raw.replace(",", ".")) < 500))
        if parsed and not _looks_like_year(parsed):
            price_from = parsed
            break

    return price_from, price_to, currency


def _infer_year_from_transcript(text: str) -> tuple[int | None, int | None]:
    haystack = norm_text(text)
    year_from: int | None = None
    year_to: int | None = None

    range_match = re.search(
        r"\b(20\d{2}|19[89]\d)\s*[-–—/]\s*(20\d{2}|19[89]\d)\b",
        haystack,
    )
    if range_match:
        y1, y2 = int(range_match.group(1)), int(range_match.group(2))
        return min(y1, y2), max(y1, y2)

    pair_match = re.search(
        r"\b(20\d{2}|19[89]\d)\s+(20\d{2}|19[89]\d)\s*(?:р(?:ок|оку|ода|оду)?|year|года|году)?\b",
        haystack,
    )
    if pair_match:
        y1, y2 = int(pair_match.group(1)), int(pair_match.group(2))
        if y1 != y2:
            return min(y1, y2), max(y1, y2)

    between_match = re.search(
        r"(?:з|с|від)\s*(20\d{2}|19[89]\d)\s*(?:по|до|-)\s*(20\d{2}|19[89]\d)",
        haystack,
    )
    if between_match:
        y1, y2 = int(between_match.group(1)), int(between_match.group(2))
        return min(y1, y2), max(y1, y2)

    for match in re.finditer(r"(?:від|з)\s*(20\d{2}|19[89]\d)", haystack):
        year_from = int(match.group(1))
        break

    for match in re.finditer(r"(?:до)\s*(20\d{2}|19[89]\d)", haystack):
        year_to = int(match.group(1))
        break

    if year_from is None:
        for match in re.finditer(r"\b(20\d{2}|19[89]\d)\s*(?:рік|року|year)\b", haystack):
            year_from = int(match.group(1))
            break

    return year_from, year_to


def _detect_search_intent(query: str, filters: dict[str, Any]) -> str | None:
    haystack = norm_text(query)
    has_budget = bool(filters.get("price_to") or filters.get("price_from"))
    has_year = bool(filters.get("year_from") or filters.get("year_to"))
    has_brand = bool(filters.get("brand"))

    discovery_keywords = (
        "найди",
        "знайди",
        "підбери",
        "подбери",
        "шукай",
        "find",
        "найкращ",
        "лучш",
        "топ",
        "варіант",
        "вариант",
        "машин",
        "авто",
    )
    has_discovery_kw = any(keyword in haystack for keyword in discovery_keywords)

    if has_budget and has_year and not has_brand:
        return "market_discovery"
    if has_budget and has_discovery_kw and not has_brand:
        return "market_discovery"
    if has_discovery_kw and has_budget and has_year:
        return "market_discovery"
    return None


def _infer_sort_from_transcript(query: str, intent: str | None) -> str | None:
    haystack = norm_text(query)
    if any(token in haystack for token in ("дешев", "дешевл", "cheaper")):
        return "price_asc"
    if any(token in haystack for token in ("лучш", "найкращ", "топ", "best", "новіш", "новее")):
        return "year_desc"
    if intent == "market_discovery":
        return "year_desc"
    return None


def _build_market_discovery_message(filters: dict[str, Any]) -> str:
    currency = str(filters.get("currency") or "USD")
    currency_label = {"USD": "$", "UAH": "₴", "EUR": "€"}.get(currency, currency)
    price_to = filters.get("price_to")
    year_from = filters.get("year_from")
    year_to = filters.get("year_to")

    budget = f"до {currency_label}{int(price_to):,}".replace(",", " ") if price_to else "у межах бюджету"
    if year_from and year_to:
        years = f"{year_from}–{year_to} р."
    elif year_from:
        years = f"від {year_from} р."
    elif year_to:
        years = f"до {year_to} р."
    else:
        years = "будь-який рік"

    return f"Пошук по ринку: {budget} · {years} · найкращі варіанти"


def _infer_region_from_transcript(text: str) -> str | None:
    haystack = norm_text(text)
    if not haystack:
        return None

    best_region: str | None = None
    best_score = 0

    for region in REGION_OPTIONS:
        if region == "Вся Україна":
            continue
        if not _region_mentioned_in_transcript(text, region):
            continue
        score = len(norm_text(region))
        if score > best_score:
            best_region = region
            best_score = score

    return best_region


_FUEL_KEYWORDS: dict[str, str] = {
    "бензин": "Бензин",
    "дизел": "Дизель",
    "електр": "Електро",
    "гіbrid": "Гібрид",
    "гібрид": "Гібрид",
    "газ": "Газ",
    "пропан": "Газ пропан+бензин",
}

_TRANSMISSION_KEYWORDS: dict[str, str] = {
    "автомат": "Автомат",
    "акpp": "Автомат",
    "механ": "Механіка",
    "механіка": "Механіка",
    "варіатор": "Варіатор",
    "cvt": "Варіатор",
    "робот": "Робот",
    "dsg": "Робот",
    "tiptronic": "Типтронік",
    "типтронік": "Типтронік",
}


def _infer_list_from_keywords(text: str, mapping: dict[str, str]) -> list[str]:
    haystack = norm_text(text)
    out: list[str] = []
    for keyword, value in mapping.items():
        if keyword in haystack and value not in out:
            out.append(value)
    return out


def _build_filter_summary(filters: dict[str, Any]) -> str:
    parts: list[str] = []

    brand = filters.get("brand")
    model = filters.get("model")
    if brand and model:
        parts.append(f"{brand} {model}")
    elif brand:
        parts.append(str(brand))

    currency = str(filters.get("currency") or "USD")
    currency_label = {"USD": "$", "UAH": "₴", "EUR": "€"}.get(currency, currency)
    price_from = filters.get("price_from")
    price_to = filters.get("price_to")
    if price_from and price_to:
        parts.append(f"{currency_label}{price_from:,}–{price_to:,}".replace(",", " "))
    elif price_to:
        parts.append(f"до {currency_label}{price_to:,}".replace(",", " "))
    elif price_from:
        parts.append(f"від {currency_label}{price_from:,}".replace(",", " "))

    year_from = filters.get("year_from")
    year_to = filters.get("year_to")
    if year_from and year_to:
        parts.append(f"{year_from}–{year_to} р.")
    elif year_from:
        parts.append(f"від {year_from} р.")
    elif year_to:
        parts.append(f"до {year_to} р.")

    mileage_to = filters.get("mileage_to")
    if mileage_to:
        parts.append(f"до {mileage_to} тис. км")

    region = filters.get("region")
    if region:
        parts.append(str(region).replace("м. ", ""))

    fuels = filters.get("fuel") or []
    if fuels:
        parts.append(", ".join(str(x) for x in fuels[:2]))

    transmissions = filters.get("transmission") or []
    if transmissions:
        parts.append(", ".join(str(x) for x in transmissions[:2]))

    if not parts:
        return ""

    return "Зрозумів: " + " · ".join(parts)


def _enrich_filters_from_transcript(
    query: str,
    filters: dict[str, Any],
    raw_filters: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(filters)
    raw_model = raw_filters.get("model")

    if not enriched.get("brand"):
        inferred = _infer_brand_from_transcript(query)
        if inferred:
            b, m = _resolve_brand_model(inferred, enriched.get("model") or raw_model)
            if b:
                enriched["brand"] = b
                if m and not enriched.get("model"):
                    enriched["model"] = m

    if enriched.get("brand") and not enriched.get("model") and raw_model:
        _, m = _resolve_brand_model(enriched["brand"], raw_model)
        if m:
            enriched["model"] = m

    if enriched.get("brand") and not enriched.get("model"):
        inferred_model = _infer_model_from_transcript(query, str(enriched["brand"]))
        if inferred_model:
            enriched["model"] = inferred_model

    if not enriched.get("region"):
        inferred_region = _infer_region_from_transcript(query)
        if inferred_region:
            enriched["region"] = inferred_region

    price_from, price_to, currency = _infer_price_from_transcript(query)
    if not enriched.get("price_from") and price_from:
        enriched["price_from"] = price_from
    if not enriched.get("price_to") and price_to:
        enriched["price_to"] = price_to
    if not enriched.get("currency") and currency:
        enriched["currency"] = currency

    year_from, year_to = _infer_year_from_transcript(query)
    if not enriched.get("year_from") and year_from:
        enriched["year_from"] = year_from
    if not enriched.get("year_to") and year_to:
        enriched["year_to"] = year_to

    if not enriched.get("fuel"):
        fuels = _infer_list_from_keywords(query, _FUEL_KEYWORDS)
        if fuels:
            enriched["fuel"] = fuels

    if not enriched.get("transmission"):
        transmissions = _infer_list_from_keywords(query, _TRANSMISSION_KEYWORDS)
        if transmissions:
            enriched["transmission"] = transmissions

    return enriched


_REGION_ALIASES: dict[str, str] = {
    "київ": "м. Київ",
    "киев": "м. Київ",
    "kyiv": "м. Київ",
    "kiev": "м. Київ",
    "львів": "Львівська область",
    "lviv": "Львівська область",
    "одеса": "Одеська область",
    "odesa": "Одеська область",
    "харків": "Харківська область",
    "dnipro": "Дніпропетровська область",
    "дніпро": "Дніпропетровська область",
    "вся україна": "Вся Україна",
    "україна": "Вся Україна",
}


def _normalize_region(region: str | None) -> str | None:
    text = str(region or "").strip()
    if not text:
        return None
    if text in REGION_OPTIONS:
        return text
    lower = text.lower()
    for key, value in _REGION_ALIASES.items():
        if key in lower:
            return value
    for option in REGION_OPTIONS:
        if option.lower() == lower:
            return option
    return text if text in REGION_OPTIONS else None


def _region_mentioned_in_transcript(text: str, region: str) -> bool:
    haystack = norm_text(text)
    if not haystack or not region:
        return False

    region_key = norm_text(region)
    if region_key == "вся україна":
        return any(
            token in haystack
            for token in ("вся україна", "по україні", "по всій україні", "ukraine")
        )

    if _text_contains_token(haystack, region_key):
        return True

    oblast_short = region_key.replace(" область", " обл")
    if oblast_short != region_key and _text_contains_token(haystack, oblast_short):
        return True

    stem = region_key.replace("м. ", "").replace(" область", "").strip()
    if len(stem) >= 4 and _text_contains_token(haystack, stem):
        return True

    for alias, mapped in _REGION_ALIASES.items():
        if mapped == region and _text_contains_token(haystack, alias):
            return True

    keywords = cities_for_region(region) or ()
    for keyword in keywords:
        token = norm_text(keyword)
        if len(token) >= 2 and _text_contains_token(haystack, token):
            return True

    return False


def _sanitize_region_from_transcript(query: str, filters: dict[str, Any]) -> dict[str, Any]:
    """Прибирає регіон, якщо GPT «додав» його, але в диктовці регіон не звучав."""
    sanitized = dict(filters)
    region = sanitized.get("region")
    if region and not _region_mentioned_in_transcript(query, str(region)):
        sanitized.pop("region", None)
    return sanitized


def _has_meaningful_filters(filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        if isinstance(value, bool) and value is False:
            continue
        if key == "category" and value == "all":
            continue
        return True
    return False


def _clean_filters(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    brand, model = _resolve_brand_model(raw.get("brand"), raw.get("model"))
    if brand:
        out["brand"] = brand
    if model:
        out["model"] = model

    category = str(raw.get("category") or "").strip()
    if category in ("used", "new", "import"):
        out["category"] = category

    region = _normalize_region(raw.get("region"))
    if region:
        out["region"] = region

    for num_key in (
        "year_from",
        "year_to",
        "price_from",
        "price_to",
        "mileage_from",
        "mileage_to",
        "engine_volume_from",
        "engine_volume_to",
        "power_from",
        "power_to",
        "owners_max",
    ):
        val = raw.get(num_key)
        if val is None or val == "":
            continue
        try:
            num = int(val) if num_key != "engine_volume_from" and num_key != "engine_volume_to" else float(val)
        except (TypeError, ValueError):
            continue
        if num_key.startswith("year") and (num < 1950 or num > 2030):
            continue
        out[num_key] = num

    currency = str(raw.get("currency") or "").strip().upper()
    if currency in ("USD", "UAH", "EUR"):
        out["currency"] = currency

    out["fuel"] = _pick_allowed(raw.get("fuels"), FUEL_OPTIONS)
    out["transmission"] = _pick_allowed(raw.get("transmissions"), TRANSMISSION_OPTIONS)
    out["drivetrain"] = _pick_allowed(raw.get("drive_types"), DRIVE_OPTIONS)
    out["body_types"] = _pick_allowed(raw.get("body_types"), BODY_TYPE_OPTIONS)
    out["colors"] = _pick_allowed(raw.get("colors"), COLOR_OPTIONS)
    out["sources"] = _pick_allowed(raw.get("sources"), SOURCE_OPTIONS)

    seller = str(raw.get("seller_filter") or "").strip()
    if seller in ("private", "dealer"):
        out["seller_filter"] = seller

    accident = str(raw.get("accident") or "").strip()
    if accident in ("none", "had"):
        out["accident"] = accident

    for bool_key in ("zero_mileage", "bargain", "vin_verified", "metallic"):
        val = raw.get(bool_key)
        if isinstance(val, bool) and val:
            out[bool_key] = True

    for tri_key in ("in_credit", "usa_import", "not_customs"):
        val = str(raw.get(tri_key) or "").strip()
        if val in ("show", "hide"):
            out[tri_key] = val

    return out


async def transcribe_audio(audio_bytes: bytes, *, filename: str = "voice.webm") -> str:
    client = _client()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    mime = {
        "webm": "audio/webm",
        "mp4": "audio/mp4",
        "m4a": "audio/mp4",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
    }.get(ext, "audio/webm")

    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes, mime),
        language="uk",
        prompt="Пошук автомобіля в Україні: марка, модель, рік, ціна, пробіг, регіон.",
    )
    return str(response.text or "").strip()


async def parse_search_text(text: str) -> dict[str, Any]:
    query = re.sub(r"\s+", " ", str(text or "").strip())
    if len(query) < 2:
        return {
            "understood": False,
            "message": "Не зрозумів — не почув запит. Спробуйте ще раз.",
            "transcript": query,
            "filters": {},
        }

    client = _client()
    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
        )
        raw_content = completion.choices[0].message.content or "{}"
        payload = json.loads(raw_content)
    except Exception:
        logger.exception("OpenAI parse_search_text failed")
        return {
            "understood": False,
            "message": "Не вдалося обробити запит. Спробуйте ще раз.",
            "transcript": query,
            "filters": {},
        }

    understood = bool(payload.get("understood"))
    message = str(payload.get("message") or "").strip()
    raw_filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
    filters = _clean_filters(raw_filters)
    filters = _enrich_filters_from_transcript(query, filters, raw_filters)
    filters = _sanitize_region_from_transcript(query, filters)

    search_intent = _detect_search_intent(query, filters)
    sort_hint = _infer_sort_from_transcript(query, search_intent)
    if sort_hint not in SORT_OPTIONS:
        sort_hint = None

    if understood and filters:
        if search_intent == "market_discovery":
            message = _build_market_discovery_message(filters)
        else:
            summary = _build_filter_summary(filters)
            if summary:
                message = summary
    elif understood and not message:
        message = "Фільтри заповнено — перевірте і натисніть «Шукати»."

    if understood and not _has_meaningful_filters(filters):
        understood = False
        message = "Не зрозумів, які саме авто шукати. Назвіть марку, модель або бюджет."

    if not understood and not message:
        message = "Не зрозумів запит. Скажіть, наприклад: «Toyota Camry до 15 тисяч доларів, від 2018 року, Київ»."

    return {
        "understood": understood,
        "message": message,
        "transcript": query,
        "filters": filters,
        "search_intent": search_intent,
        "sort": sort_hint,
    }
