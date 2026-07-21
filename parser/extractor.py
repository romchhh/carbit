"""
Екстрактор даних про авто з довільного, часто криво написаного тексту.

Головний принцип: канали пишуть оголошення по-різному (хтось акуратно
"Марка Модель Рік / Двигун / Пробіг / Ціна / Місто / Телефон", хтось суцільним
текстом без розділових знаків, хтось капсом, хтось сумішшю укр/рос).
Тому extractor НІКОЛИ не падає і не викидає виключення - якщо якесь поле
не знайдено, воно просто залишається None, а raw_text зберігається завжди.

Немає жорсткого формату вхідних даних - є набір незалежних регексп-евристик,
кожна з яких намагається знайти "своє" поле незалежно від інших.
"""
import re
from datetime import datetime
from typing import Optional

from .brands_data import CAR_BRANDS, BRAND_CANONICAL
from .cities import UKRAINE_CITIES, CITY_CANONICAL
from .models import CarListing

CURRENT_YEAR = datetime.now().year

# Бренди, для яких потрібні межі слова (щоб не ловити "man" у "roman", "mini" у "minimal")
WORD_BOUNDARY_BRANDS = {
    "man", "ман", "vw", "kia", "кіа", "киа", "gmc", "daf", "даф", "byd", "mini", "міні",
    "ev", "seat", "сеат", "opel", "опель", "geely", "джили", "nio", "li",
}

MIN_LISTING_CONFIDENCE = 0.33

SPAM_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"вебінар",
        r"webinar",
        r"підпиш(?:ись|іться)",
        r"подпис(?:ывай|ывайтесь|аться)",
        r"хочеш\s+продати\s+авто",
        r"продай\s+(?:сво[єe]\s+)?авто",
        r"навчання\s+(?:з\s+)?(?:продаж|авто)",
        r"тренінг",
        r"реклам(?:а|ний|не)",
        r"спонсор",
        r"promокод",
        r"giveaway",
        r"розіграш",
        r"наш\s+канал",
        r"переход(?:ь|ьте)\s+по\s+посилан",
        r"безкоштовн(?:ий|а)\s+(?:курс|урок)",
        r"криптовалют",
        r"обмін\s+квартир",
        r"здаю\s+в\s+оренду",
        r"вакансія",
        r"набір\s+в\s+команду",
    )
]

# Запит «шукаю авто», а не пропозиція продажу
SEARCH_REQUEST_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"#?\s*пошук\s+авто",
        r"#?\s*ищу\s+авто",
        r"#?\s*шукаю\s+авто",
        r"шукає(?:мо)?\s+(?:авто|машин|автомоб|[А-ЯЁІЇЄA-Z])",
        r"шукаю\s+(?:авто|машин|автомоб)",
        r"ищу\s+(?:авто|машин|автомоб)",
        r"куплю\s+(?:авто|машин|автомоб)",
        r"купимо\s+(?:авто|машин|автомоб)",
        r"терміново\s+шукаємо",
        r"терміново\s+шукаю",
        r"срочно\s+(?:ищу|ищем)",
        r"маєте\s+(?:таке|таку|такий)?\s*авто",
        r"є\s+(?:у\s+вас\s+)?(?:таке|таку|такий)?\s*авто",
        r"в\s+пошуках",
        r"в\s+поиске",
        r"buying\s+car",
        r"wanted\s+car",
        r"розшук\s+авто",
        r"🚨\s*терміново\s+шукаємо",
    )
]

_BUYER_YEAR_RE = re.compile(
    r"\b(?:от|from)\s+(?:19|20)\d{2}\s*г\.?\s*в\.?",
    re.IGNORECASE,
)
_BUDGET_CAP_LINE_RE = re.compile(
    r"[-–—]\s*до\s*\d{1,3}\s*[\$€]",
    re.IGNORECASE,
)
_MAX_BUDGET_RE = re.compile(r"\bдо\s*\d{1,3}\s*[\$€]", re.IGNORECASE)
_SALE_KEYWORDS = (
    "продам",
    "продаю",
    "продається",
    "продается",
    "на продаж",
    "for sale",
    "sale ",
)

# --- окремі regex-и на кожне поле ---------------------------------------

# Рік: 2021, 2021г, 2021г., 2021 рік, 20 21 (рідко)
YEAR_RE = re.compile(
    r"(?<!\d)(19[5-9]\d|20[0-3]\d|20 ?[0-3]\d)(?!\d)"
    r"(?:\s*(?:[гg]\.?(?:ода?|од)?|рік|року|р\.?))?",
    re.IGNORECASE,
)

# ціна: $12 000, 12000$, 12 000 usd, 350000 грн, 12000 у.е., €9500, MMR: $7,350
PRICE_RE = re.compile(
    r"(?:"
    r"(?P<label>mmr|ціна|цена|price|💰|💵|💲)\s*:?\s*"
    r")?"
    r"(?P<cur_before>[\$€])?\s?"
    r"(?P<amount>\d{1,3}(?:[ .,]\d{3})+(?:[.,]\d{1,2})?|\d{4,8})"
    r"\s?(?P<cur_after>\$|€|грн\.?|uah|usd|eur|у\.?\s?е\.?)?",
    re.IGNORECASE,
)

MILEAGE_RE = re.compile(
    r"(?P<val>\d{1,3}(?:[ .,]\d{3})?)\s?"
    r"(?P<unit>тис\.?\s?км|тыс\.?\s?км|км)",
    re.IGNORECASE,
)

MILEAGE_MILES_RE = re.compile(
    r"(?P<val>\d{1,3}(?:[ .,]\d{3})?)\s?(?:miles|mil\b|миль)",
    re.IGNORECASE,
)

ENGINE_RE = re.compile(r"(?P<val>\d[.,]\d)\s?л\b", re.IGNORECASE)

POWER_RE = re.compile(r"(?P<val>\d{2,4})\s?(?:к\.?\s?с\.?|hp|л\.?с\.?)", re.IGNORECASE)

PHONE_RE = re.compile(
    r"(?:\+?38)?0\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b"
)

USERNAME_RE = re.compile(r"@([A-Za-z0-9_]{4,32})")

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKDOWN_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
# Хештег → токен: #Zeekr→Zeekr, #L6T79…→VIN; не видаляємо зміст.
HASHTAG_RE = re.compile(r"#([A-Za-zА-Яа-яЇїІіЄєҐґ0-9_\-]{1,64})")
VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
_VIN_LABELED_RE = re.compile(
    r"(?:vin|він|вин(?:[\s\-]*код)?)\s*[:\-–—]?\s*([A-HJ-NPR-Z0-9]{17})",
    re.IGNORECASE,
)
_VIN_HASHTAG_RE = re.compile(r"#([A-HJ-NPR-Z0-9]{17})\b", re.IGNORECASE)


def _extract_vin(text: str) -> str | None:
    if not text:
        return None
    for match in _VIN_HASHTAG_RE.finditer(text):
        candidate = match.group(1).upper()
        if "I" not in candidate and "O" not in candidate and "Q" not in candidate:
            return candidate
    labeled = _VIN_LABELED_RE.search(text)
    if labeled:
        candidate = labeled.group(1).upper()
        if "I" not in candidate and "O" not in candidate and "Q" not in candidate:
            return candidate
    for match in VIN_RE.finditer(text.upper()):
        candidate = match.group(0)
        if "I" not in candidate and "O" not in candidate and "Q" not in candidate:
            return candidate
    return None


def _hashtag_replacer(match: re.Match) -> str:
    tag = match.group(1)
    if re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", tag, re.IGNORECASE):
        return tag.upper()
    return tag


MILEAGE_FULL_KM_RE = re.compile(
    r"(?P<val>\d{2,3}(?:[ .]\d{3})+|\d{4,7})\s*км",
    re.IGNORECASE,
)

# UA shorthand: «13к пробіг», «13 к км», «пробіг 13к»
MILEAGE_SHORT_K_RE = re.compile(
    r"(?:"
    r"(?P<val>\d{1,3}(?:[ .,]\d{3})?)\s*[кk]\.?\s*(?:км\b|(?:проб[іi]г|пробег)\b)"
    r"|"
    r"(?:проб[іi]г|пробег)\s*:?\s*(?P<val2>\d{1,3}(?:[ .,]\d{3})?)\s*[кk]\.?\b"
    r")",
    re.IGNORECASE,
)

PRICE_LABEL_RE = re.compile(
    r"(?:ціна|цена|price|💰|💵|💲)\s*:?\s*"
    r"(?P<amount>\d{1,3}(?:[ .,]\d{3})+|\d{3,8})"
    r"\s?(?P<cur>[\$€]|грн\.?|uah|usd|eur|у\.?\s?е\.?)?",
    re.IGNORECASE,
)

MILEAGE_LABEL_RE = re.compile(
    r"(?:пробіг|пробег|mileage|📏)[ \t]*:?[ \t]*"
    r"(?P<val>\d{1,3}(?:[ .,]\d{3})?)[ \t]*"
    r"(?P<unit>тис\.?[ \t]?км|тыс\.?[ \t]?км|км)?",
    re.IGNORECASE,
)

MODEL_STOP_WORDS = frozenset({
    "рік", "года", "року", "р", "р.", "ціна", "цена", "price", "пробіг", "пробег",
    "бензин", "дизель", "газ", "автомат", "механіка", "механика", "типтронік",
    "тип", "кузов", "седан", "хетчбек", "продаю", "продам", "sale",
})

TRANSMISSION_MAP = {
    "механіка": "manual", "механика": "manual", "ручна": "manual", "мкпп": "manual",
    "автомат": "automatic", "акпп": "automatic", "typtronic": "automatic", "типтронік": "automatic",
    "варіатор": "variator", "вариатор": "variator", "cvt": "variator",
    "робот": "robot", "dsg": "robot", "dct": "robot",
}

DRIVE_MAP = {
    "повний привід": "awd", "повний": "awd", "4x4": "awd", "awd": "awd", "4wd": "awd",
    "передній привід": "fwd", "передній": "fwd", "fwd": "fwd",
    "задній привід": "rwd", "задній": "rwd", "rwd": "rwd",
}

FUEL_MAP = {
    "бензин": "petrol", "petrol": "petrol", "gasoline": "petrol",
    "дизель": "diesel", "дизел": "diesel", "diesel": "diesel",
    "газ/бензин": "gas_petrol", "газ": "gas", "гбо": "gas", "lpg": "gas",
    "гібрид": "hybrid", "гибрид": "hybrid", "hybrid": "hybrid",
    "електро": "electric", "электро": "electric", "electric": "electric", "ev": "electric",
}

CONDITION_KEYWORDS = {
    "not_damaged": ["не бита", "не бит", "не крашена", "не крашен", "без дтп", "не в дтп", "не аварійна"],
    "damaged": ["бита", "потребує ремонту", "після дтп", "аварийна", "аварійна", "требует ремонта"],
    "customs_cleared": ["розмитнено", "розмитнена", "растаможен", "на укр номерах", "на єврономерах"],
    "not_customs_cleared": ["без розмитнення", "не розмитнена", "на транзитах", "без растаможки"],
    "on_sale": ["терміново", "срочно", "торг", "без торгу", "торг доречний"],
}


def normalize_listing_text(raw_text: str) -> str:
    """Прибирає markdown; хештеги лишає як звичайні токени (VIN — окремо)."""
    text = raw_text or ""
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = MARKDOWN_BOLD_RE.sub(r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = HASHTAG_RE.sub(_hashtag_replacer, text)
    text = re.sub(r"[\u00a0\u202f\u2009]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_promo_or_spam(text_low: str) -> bool:
    if not text_low.strip():
        return False
    return any(pattern.search(text_low) for pattern in SPAM_PATTERNS)


def is_car_search_request(text: str) -> bool:
    """True, якщо пост — запит на купівлю («шукаю X5 до 65$»), а не оголошення продажу."""
    raw = (text or "").strip()
    if not raw:
        return False
    text_low = raw.lower()

    if any(pattern.search(raw) for pattern in SEARCH_REQUEST_PATTERNS):
        return True
    if "🕵" in raw and ("пошук" in text_low or "ищу" in text_low or "шукаю" in text_low):
        return True
    if "🚨" in raw and ("шукаємо" in text_low or "шукаю" in text_low or "ищем" in text_low):
        return True

    budget_lines = len(_BUDGET_CAP_LINE_RE.findall(raw))
    max_budget_hits = len(_MAX_BUDGET_RE.findall(raw))
    has_buyer_year = bool(_BUYER_YEAR_RE.search(raw))
    considers = any(
        kw in text_low
        for kw in ("рассмотр", "розглян", "also consider", "також розгляну", "также рассмотр")
    )
    has_sale_intent = any(kw in text_low for kw in _SALE_KEYWORDS)

    if has_buyer_year and (budget_lines >= 1 or max_budget_hits >= 2 or considers):
        return True

    if not has_sale_intent and budget_lines >= 2:
        return True

    if not has_sale_intent and considers and (budget_lines >= 1 or max_budget_hits >= 1):
        return True

    return False


def is_valid_car_listing(listing: CarListing) -> bool:
    """Чи варто зберігати/показувати оголошення (відсікає рекламу та порожні альбоми)."""
    text = (listing.raw_text or "").strip()
    text_low = text.lower()

    if not text and listing.confidence <= 0:
        return False

    if is_car_search_request(text):
        return False

    if is_promo_or_spam(text_low):
        return False

    has_brand = bool(listing.brand)
    has_year = listing.year is not None
    has_price = listing.price_amount is not None
    has_mileage = listing.mileage_km is not None

    if has_brand and (has_year or has_price):
        return listing.confidence >= MIN_LISTING_CONFIDENCE

    if has_price and has_year and (has_mileage or listing.engine_volume_l):
        return True

    if listing.confidence >= 0.5:
        return True

    return False


def _normalize_amount(raw: str) -> Optional[float]:
    cleaned = raw.replace(" ", "").replace(",", "")
    # варіант "12.000" (крапка як роздільник тисяч) vs "12.5" (дробове - малоймовірне для ціни авто)
    if cleaned.count(".") == 1 and len(cleaned.split(".")[1]) == 3:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _brand_match(text_low: str, brand_key: str) -> Optional[int]:
    if brand_key in WORD_BOUNDARY_BRANDS or len(brand_key) <= 3:
        pattern = re.compile(
            rf"(?<![a-zа-яёєіїґ0-9\-]){re.escape(brand_key)}(?![a-zа-яёєіїґ0-9\-])",
            re.IGNORECASE,
        )
        match = pattern.search(text_low)
        return match.start() if match else None
    idx = text_low.find(brand_key)
    return idx if idx != -1 else None


def _find_brand_model(text_low: str, original_text: str):
    """Шукає бренд у тексті і намагається витягти 1-2 наступних слова як модель."""
    for brand_key in CAR_BRANDS:
        idx = _brand_match(text_low, brand_key)
        if idx is None:
            continue
        brand = BRAND_CANONICAL.get(brand_key, brand_key.title())
        tail = original_text[idx + len(brand_key): idx + len(brand_key) + 40]
        words = re.findall(r"[A-Za-zА-Яа-яЇїІіЄєҐґ0-9\-]+", tail)
        model_words = []
        for w in words[:3]:
            if YEAR_RE.fullmatch(w) or YEAR_RE.match(w):
                break
            if w.lower() in MODEL_STOP_WORDS:
                break
            if w.lower() in ("рік", "года", "року", "р", "р.", "г", "г."):
                break
            model_words.append(w)
            if len(model_words) >= 2:
                break
        model = " ".join(model_words) if model_words else None
        return brand, model, idx
    return None, None, None


def _find_year(text: str, brand_pos_hint: Optional[int] = None) -> Optional[int]:
    candidates = []
    for m in YEAR_RE.finditer(text):
        val = int(m.group(1).replace(" ", ""))
        if 1950 <= val <= CURRENT_YEAR + 1:
            candidates.append((m.start(), val))
    if not candidates:
        return None
    if brand_pos_hint is not None:
        candidates.sort(key=lambda c: abs(c[0] - brand_pos_hint))
        return candidates[0][1]
    return candidates[0][1]


def _price_in_range(amount: float, currency: Optional[str]) -> bool:
    if currency == "UAH":
        return 10_000 <= amount <= 15_000_000
    if currency in ("USD", "EUR"):
        return 100 <= amount <= 500_000
    # без явної валюти — ширший діапазон, щоб не відкинути реальні оголошення
    return 500 <= amount <= 3_000_000


def _looks_like_year(amount: float) -> bool:
    if amount != int(amount):
        return False
    year = int(amount)
    return 1950 <= year <= CURRENT_YEAR + 1


def _looks_like_phone_amount(amount: float) -> bool:
    if amount != int(amount):
        return False
    digits = str(int(amount))
    return len(digits) >= 10 and digits.startswith("0")


def _find_price(text: str):
    # Кілька 💰 (стара/нова ціна) — беремо останню валідну (часто акційна).
    labeled_hits: list[tuple[float, str | None]] = []
    for label_match in PRICE_LABEL_RE.finditer(text):
        amount = _normalize_amount(label_match.group("amount"))
        if amount is None or _looks_like_phone_amount(amount):
            continue
        cur = (label_match.group("cur") or "").lower()
        currency = None
        if cur in ("$", "usd") or "у" in cur:
            currency = "USD"
        elif cur in ("€", "eur"):
            currency = "EUR"
        elif "грн" in cur or cur == "uah":
            currency = "UAH"
        if _price_in_range(amount, currency):
            if currency is None:
                from .currency import infer_currency
                currency = infer_currency(amount, None, text)
            labeled_hits.append((amount, currency))
    if labeled_hits:
        return labeled_hits[-1]

    best = None
    best_score = -1
    for m in PRICE_RE.finditer(text):
        amount = _normalize_amount(m.group("amount"))
        if amount is None:
            continue

        if _looks_like_phone_amount(amount):
            continue

        cur = (m.group("cur_before") or m.group("cur_after") or "").lower()
        currency = None
        if cur in ("$", "usd"):
            currency = "USD"
        elif cur in ("€", "eur"):
            currency = "EUR"
        elif "грн" in cur or cur == "uah":
            currency = "UAH"
        elif "у" in cur and "е" in cur:
            currency = "USD"

        has_label = bool(m.group("label"))
        if _looks_like_year(amount) and not currency and not has_label:
            continue

        if not _price_in_range(amount, currency):
            continue

        score = 0
        if currency:
            score += 2
        if has_label:
            score += 3
        if best is None or score > best_score:
            best = (amount, currency)
            best_score = score

    if best is None:
        return None, None

    amount, currency = best
    if currency is None:
        from .currency import infer_currency

        currency = infer_currency(amount, None, text)
    return amount, currency


def _find_mileage(text: str) -> Optional[int]:
    label = MILEAGE_LABEL_RE.search(text)
    if label:
        val = _normalize_amount(label.group("val"))
        if val is not None:
            unit = (label.group("unit") or "").lower()
            if unit and ("тис" in unit or "тыс" in unit):
                return int(val * 1000)
            if val < 1000:
                return int(val * 1000)
            return int(val)

    short = MILEAGE_SHORT_K_RE.search(text)
    if short:
        raw = short.group("val") or short.group("val2")
        val = _normalize_amount(raw) if raw else None
        if val is not None and 1 <= val <= 999:
            return int(val * 1000)

    m = MILEAGE_RE.search(text)
    if m:
        val = _normalize_amount(m.group("val"))
        if val is not None:
            unit = m.group("unit").lower()
            if "тис" in unit or "тыс" in unit:
                val *= 1000
            return int(val)

    full_km = MILEAGE_FULL_KM_RE.search(text)
    if full_km:
        val = _normalize_amount(full_km.group("val"))
        if val is not None:
            return int(val)

    miles = MILEAGE_MILES_RE.search(text)
    if miles:
        val = _normalize_amount(miles.group("val"))
        if val is not None:
            return int(val * 1609.34)
    return None


def _find_mapped(text_low: str, mapping: dict) -> Optional[str]:
    for key, value in mapping.items():
        if key in text_low:
            return value
    return None


def _find_city(text_low: str) -> Optional[str]:
    for key in UKRAINE_CITIES:
        if key in text_low:
            return CITY_CANONICAL.get(key, key.title())
    return None


def _find_condition_flags(text_low: str) -> dict:
    flags = {}
    for flag_name, keywords in CONDITION_KEYWORDS.items():
        if any(kw in text_low for kw in keywords):
            flags[flag_name] = True
    return flags


def extract_car_data(
    raw_text: str,
    channel: str,
    message_id: int,
    group_message_ids: list,
    source_link: str,
    posted_at: Optional[datetime],
    photos: list,
) -> CarListing:
    """
    Головна функція модуля. Ніколи не кидає виключення назовні -
    в найгіршому випадку поверне CarListing з порожніми полями і
    needs_review=True, зберігши raw_text для ручного розбору/повторної обробки.
    """
    text = normalize_listing_text(raw_text)
    text_low = text.lower()

    listing = CarListing(
        channel=channel,
        message_id=message_id,
        group_message_ids=group_message_ids,
        source_link=source_link,
        posted_at=posted_at,
        raw_text=text,
        photos=photos,
    )

    try:
        # VIN часто лише в хештегу — шукаємо до і після нормалізації.
        vin_early = _extract_vin(raw_text or "")

        brand, model, brand_pos = _find_brand_model(text_low, text)
        listing.brand = brand
        listing.model = model

        listing.year = _find_year(text, brand_pos)

        amount, currency = _find_price(text_low)
        listing.price_amount = amount
        listing.price_currency = currency

        listing.mileage_km = _find_mileage(text_low)

        eng = ENGINE_RE.search(text_low)
        if eng:
            listing.engine_volume_l = float(eng.group("val").replace(",", "."))

        power = POWER_RE.search(text_low)
        if power:
            listing.power_hp = int(power.group("val"))

        listing.transmission = _find_mapped(text_low, TRANSMISSION_MAP)
        listing.drive_type = _find_mapped(text_low, DRIVE_MAP)
        listing.fuel_type = _find_mapped(text_low, FUEL_MAP)
        listing.location_city = _find_city(text_low)

        phone_m = PHONE_RE.search(text)
        listing.phone = phone_m.group(0) if phone_m else None

        user_m = USERNAME_RE.search(text)
        listing.contact_username = user_m.group(1) if user_m else None

        listing.condition_flags = _find_condition_flags(text_low)

        vin = vin_early or _extract_vin(text)
        if vin:
            listing.condition_flags = {**(listing.condition_flags or {}), "vin": vin}

        key_fields = [listing.brand, listing.year, listing.price_amount]
        found_key = sum(1 for f in key_fields if f is not None)
        secondary_fields = [
            listing.mileage_km, listing.phone, listing.location_city,
            listing.fuel_type, listing.transmission,
        ]
        found_secondary = sum(1 for f in secondary_fields if f is not None)

        listing.confidence = round(
            (found_key / 3) * 0.7 + (found_secondary / len(secondary_fields)) * 0.3, 2
        )
        listing.needs_review = found_key < 2 or is_promo_or_spam(text_low) or is_car_search_request(text)

    except Exception:
        listing.needs_review = True
        listing.confidence = 0.0

    return listing
