"""Розпізнавання голосового/текстового запиту пошуку авто через OpenAI."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.search.fe_catalog import load_fe_brand_models, fe_brand_slug_to_label, unique_model_token_owner
from app.services.olx.brand_slugs import resolve_olx_brand_slug
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

SYSTEM_PROMPT = f"""Ти — асистент пошуку авто на Carbit (Україна). Користувач диктує або пише, що шукати.
Розбери запит у структуровані фільтри. Відповідай ТІЛЬКИ валідним JSON.

Правила:
- Якщо запит не про пошук авто, зовсім незрозумілий або порожній — understood=false, message українською («Не зрозумів…» + що саме неясно).
- Якщо зрозуміло хоча б марку, модель, ціну, рік, регіон або інший параметр — understood=true.
- brand і model — точні назви з каталогу (латиниця для марок: Toyota, BMW, Volkswagen тощо).
- category: all | used | new | import (вживане/нове/під пригон).
- currency: USD | UAH | EUR (за замовчуванням USD, якщо сказали «гривень/грн» — UAH, «євро» — EUR).
- price_from/price_to, year_from/year_to — числа.
- mileage_from/mileage_to — пробіг у тисячах км (напр. «до 100 тисяч» → mileage_to=100).
- fuels, transmissions, drive_types, body_types, colors, sources — масиви з дозволених значень.
- region — одне з дозволених (м. Київ, Львівська область тощо).
- seller_filter: private | dealer | null; accident: none | had | null.
- zero_mileage, bargain, vin_verified, metallic — boolean.
- owners_max: 1 | 2 | 3 | 4 | null (4 = 4+ власників).
- in_credit, usa_import, not_customs: show | hide | null.
- Невказані поля — null або [] (не вигадуй).

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


def _normalize_region(region: str | None) -> str | None:
    text = str(region or "").strip()
    if not text:
        return None
    if text in REGION_OPTIONS:
        return text
    lower = text.lower()
    aliases = {
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
    for key, value in aliases.items():
        if key in lower:
            return value
    for option in REGION_OPTIONS:
        if option.lower() == lower:
            return option
    return text if text in REGION_OPTIONS else None


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

    if understood and not _has_meaningful_filters(filters):
        understood = False
        if not message:
            message = "Не зрозумів, які саме авто шукати. Назвіть марку, модель або бюджет."

    if not understood and not message:
        message = "Не зрозумів запит. Скажіть, наприклад: «Toyota Camry до 15 тисяч доларів, від 2018 року, Київ»."

    return {
        "understood": understood,
        "message": message,
        "transcript": query,
        "filters": filters,
    }
