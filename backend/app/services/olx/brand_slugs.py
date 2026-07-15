from __future__ import annotations

import re

from app.core.text import norm_text as _norm
from app.services.olx.olx_model_catalog import (
    OLX_EMPTY_MODEL_TAXONOMY_BRANDS,
    OLX_FE_MODEL_REMAP,
    OLX_FE_TEXT_MODELS,
    OLX_KNOWN_MODEL_PATHS,
)


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_/]+", "-", text)
    return text.strip("-")


# Ключ — нормалізована назва (uk/ru/en), значення — slug у URL OLX
BRAND_TO_SLUG: dict[str, str] = {
    # Latin
    "acura": "acura",
    "alfa romeo": "alfa-romeo",
    "aston martin": "aston-martin",
    "audi": "audi",
    "baic": "baic",
    "bentley": "bentley",
    "bmw": "bmw",
    "buick": "buick",
    "byd": "byd",
    "cadillac": "cadillac",
    "changan": "changan",
    "chery": "chery",
    "chevrolet": "chevrolet",
    "chrysler": "chrysler",
    "citroen": "citroen",
    "citroën": "citroen",
    "cupra": "cupra",
    "dacia": "dacia",
    "daewoo": "daewoo",
    "daf": "daf",
    "dodge": "dodge",
    "dongfeng": "dongfeng",
    "ds": "ds",
    "fiat": "fiat",
    "ford": "ford",
    "foton": "foton",
    "gac": "gac",
    "geely": "geely",
    "genesis": "genesis",
    "gmc": "gmc",
    "great wall": "great-wall",
    "haval": "haval",
    "honda": "honda",
    "hummer": "hummer",
    "hyundai": "hyundai",
    "infiniti": "infiniti",
    "isuzu": "isuzu",
    "iveco": "iveco",
    "jaguar": "jaguar",
    "jeep": "jeep",
    "kia": "kia",
    "lada": "lada",
    "lamborghini": "lamborghini",
    "lancia": "lancia",
    "land rover": "land-rover",
    "lexus": "lexus",
    "lincoln": "lincoln",
    "lotus": "lotus",
    "maserati": "maserati",
    "mazda": "mazda",
    "mclaren": "mclaren",
    "mercedes": "mercedes-benz",
    "mercedes-benz": "mercedes-benz",
    "mercedes benz": "mercedes-benz",
    # Народне написання на OLX.ua (/q-mersedes-gla/)
    "mersedes": "mercedes-benz",
    "mersedes-benz": "mercedes-benz",
    "mersedes benz": "mercedes-benz",
    "mg": "mg",
    "mini": "mini",
    "mitsubishi": "mitsubishi",
    "nissan": "nissan",
    "opel": "opel",
    "peugeot": "peugeot",
    "porsche": "porsche",
    "renault": "renault",
    "rolls-royce": "rolls-royce",
    "rolls royce": "rolls-royce",
    "rover": "rover",
    "saab": "saab",
    "seat": "seat",
    "skoda": "skoda",
    "škoda": "skoda",
    "smart": "smart",
    "ssangyong": "ssangyong",
    "subaru": "subaru",
    "suzuki": "suzuki",
    "tesla": "tesla",
    "toyota": "toyota",
    "volkswagen": "volkswagen",
    "vw": "volkswagen",
    "volvo": "volvo",
    "zaz": "zaz",
    "zeekr": "zeekr",
    "зікр": "zeekr",
    "зикр": "zeekr",
    "зеекр": "zeekr",
    "nio": "nio",
    "xpeng": "xpeng",
    "li auto": "li-auto",
    "li": "li-auto",
    "voyah": "voyah",
    "avatr": "avatr",
    "deepal": "deepal",
    "aito": "aito",
    "hongqi": "hongqi",
    "leapmotor": "leapmotor",
    "skywell": "skywell",
    "seres": "seres",
    "ora": "ora",
    "tank": "tank",
    "gwm": "gwm",
    "jaecoo": "jaecoo",
    "omoda": "omoda",
    "jetour": "jetour",
    "exeed": "exeed",
    "lucid": "lucid",
    "rivian": "rivian",
    "vinfast": "vinfast",
    "polestar": "polestar",
    "lynk & co": "lynk-and-co",
    "lynk and co": "lynk-and-co",
    "wey": "wey",
    # Ukrainian / Russian
    "ауді": "audi",
    "ауди": "audi",
    "бмв": "bmw",
    "бмв": "bmw",
    "мерседес": "mercedes-benz",
    "мерседес-бенц": "mercedes-benz",
    "мерседес бенц": "mercedes-benz",
    "фольксваген": "volkswagen",
    "фольксваген": "volkswagen",
    "тойота": "toyota",
    "тойота": "toyota",
    "хонда": "honda",
    "хюндай": "hyundai",
    "хёндай": "hyundai",
    "хендай": "hyundai",
    "кіа": "kia",
    "кия": "kia",
    "ніссан": "nissan",
    "ниссан": "nissan",
    "форд": "ford",
    "шкода": "skoda",
    "шкода": "skoda",
    "рено": "renault",
    "пежо": "peugeot",
    "сітроен": "citroen",
    "ситроен": "citroen",
    "опель": "opel",
    "мазда": "mazda",
    "субару": "subaru",
    "лексус": "lexus",
    "лексус": "lexus",
    "вольво": "volvo",
    "волво": "volvo",
    "міцубісі": "mitsubishi",
    "митсубиси": "mitsubishi",
    "митсубиши": "mitsubishi",
    "шевроле": "chevrolet",
    "шевроле": "chevrolet",
    "даewoo": "daewoo",
    "деву": "daewoo",
    "дэу": "daewoo",
    "лада": "lada",
    "ваз": "lada",
    "заз": "zaz",
    "порше": "porsche",
    "ягуар": "jaguar",
    "джип": "jeep",
    "ленд ровер": "land-rover",
    "лендровер": "land-rover",
    "інфініті": "infiniti",
    "инфинити": "infiniti",
    "акура": "acura",
    "бентлі": "bentley",
    "бентли": "bentley",
    "фіат": "fiat",
    "фиат": "fiat",
    "додж": "dodge",
    "крайслер": "chrysler",
    "тесла": "tesla",
}

# Модель без прив'язки до марки
MODEL_TO_SLUG: dict[str, str] = {
    "passat": "passat",
    "пасат": "passat",
    "octavia": "octavia",
    "октавія": "octavia",
    "октавия": "octavia",
    "camry": "camry",
    "камрі": "camry",
    "камри": "camry",
    "rav4": "rav-4",
    "rav-4": "rav-4",
    "рав4": "rav-4",
    "corolla": "corolla",
    "корола": "corolla",
    "королла": "corolla",
    "a4": "a4",
    "а4": "a4",
    "a6": "a6",
    "а6": "a6",
    "a3": "a3",
    "а3": "a3",
    "a5": "a5",
    "а5": "a5",
    "q5": "q5",
    "q7": "q7",
    "q3": "q3",
    "x5": "x5",
    "х5": "x5",
    "x3": "x3",
    "x6": "x6",
    "x7": "x7",
    "tiguan": "tiguan",
    "тігуан": "tiguan",
    "тигуан": "tiguan",
    "golf": "golf",
    "гольф": "golf",
    "polo": "polo",
    "поло": "polo",
    "touareg": "touareg",
    "туарег": "touareg",
    "touareg": "touareg",
    "cx-5": "cx-5",
    "cx5": "cx-5",
    "tucson": "tucson",
    "тусон": "tucson",
    "sportage": "sportage",
    "спортейдж": "sportage",
    "спортаж": "sportage",
    "ceed": "ceed",
    "сід": "ceed",
    "ceed": "ceed",
    "focus": "focus",
    "фокус": "focus",
    "mondeo": "mondeo",
    "мондео": "mondeo",
    "fusion": "fusion",
    "фьюжн": "fusion",
    "fiesta": "fiesta",
    "фієста": "fiesta",
    "фиеста": "fiesta",
    "kuga": "kuga",
    "куга": "kuga",
    "cr-v": "cr-v",
    "crv": "cr-v",
    "civic": "civic",
    "сивік": "civic",
    "сивик": "civic",
    "accord": "accord",
    "акорд": "accord",
    "e-tron": "e-tron",
    "етрон": "e-tron",
}

# Ручні аліаси (кирилиця / рідкісні). FE-каталог → olx_model_catalog.OLX_FE_MODEL_REMAP
_BRAND_MODEL_HAND: dict[str, str] = {
    "бмв|1 series": "1-serya",
    "бмв|3 series": "3-serya",
    "бмв|5 series": "5-serya",
    "мерседес|a-class": "a-seriya",
    "мерседес|b-class": "b-seriya",
    "мерседес|c-class": "c-seriya",
    "мерседес|e-class": "e-seriya",
    "мерседес|s-class": "s-seriya",
    "мерседес|g-class": "g-seriya",
    "мерседес|m-class": "ml-seriya",
    "мерседес|coupe": "coupe",
    "мерседес|купе": "coupe",
    "мерседес|cabrio": "cabrio",
    "мерседес|кабріо": "cabrio",
    "мерседес-бенц|c-class": "c-seriya",
    "мерседес-бенц|e-class": "e-seriya",
    "мерседес-бенц|s-class": "s-seriya",
    "мерседес-бенц|coupe": "coupe",
    "мерседес-бенц|купе": "coupe",
}

_SERIES_RE = re.compile(
    r"^(\d+)\s*(?:series|серії|серии|серія|серия|seriya|serya)?$",
    re.IGNORECASE,
)

# FE remap поверх ручних (латиниця з live scrape)
BRAND_MODEL_TO_SLUG: dict[str, str] = {**_BRAND_MODEL_HAND, **OLX_FE_MODEL_REMAP}


# Slug у path OLX, які дають 404 (перевірено live 2026-07). Шукаємо через /q-.../
# BYD має /byd/ path — не тут; моделі BYD без path → OLX_EMPTY_MODEL_TAXONOMY_BRANDS.
OLX_TEXT_SEARCH_SLUGS = frozenset(
    {
        "aito",
        "avatr",
        "baic",
        "bugatti",
        "changan",
        "cupra",
        "daf",
        "datsun",
        "deepal",
        "dfsk",
        "dongfeng",
        "ds",
        "exeed",
        "forthing",
        "foton",
        "gac",
        "genesis",
        "gwm",
        "haval",
        "hongqi",
        "jaecoo",
        "jetour",
        "lada",
        "leapmotor",
        "li-auto",
        "lucid",
        "lynk-and-co",
        "man",
        "nio",
        "omoda",
        "ora",
        "rivian",
        "scania",
        "seres",
        "skywell",
        "tank",
        "vinfast",
        "voyah",
        "wey",
        "xpeng",
        "zeekr",
    }
)

# Додаткові нормалізовані імена (як у фільтрі FE), якщо slug інший
OLX_TEXT_SEARCH_NAMES = frozenset(
    {
        "li auto",
        "li",
        "lynk & co",
        "lynk and co",
        "great wall motor",
        "gwm",
        "x peng",
        "xpeng",
        "nio",
        "zeekr",
        "зікр",
        "зикр",
        "зеекр",
        "jaecoo",
        "omoda",
        "jetour",
        "haval",
        "changan",
        "dongfeng",
        "voyah",
        "skywell",
        "cupra",
        "genesis",
        "baic",
        "gac",
        "foton",
        "lada",
        "ваз",
        "лада",
    }
)


def brand_uses_olx_text_search(brand: str) -> bool:
    """True, якщо /brand/ на OLX.ua не працює → потрібен текстовий /q-.../."""
    key = _norm(brand)
    if key in OLX_TEXT_SEARCH_NAMES or key in OLX_TEXT_SEARCH_SLUGS:
        return True
    slug = BRAND_TO_SLUG.get(key) or slugify(brand)
    return bool(slug) and slug in OLX_TEXT_SEARCH_SLUGS


def brand_model_forces_text_search(brand: str, model: str) -> bool:
    """True, якщо марка+модель без підтвердженого /brand/model/ → одразу /q-.../.

    Покриває весь FE-каталог (~1400 моделей): або path з OLX_FE_MODEL_REMAP,
    або text з OLX_FE_TEXT_MODELS / empty taxonomy.
    """
    model_key = _norm(model)
    if not model_key:
        return False
    brand_key = _norm(brand)
    brand_slug = BRAND_TO_SLUG.get(brand_key, slugify(brand)) if brand else ""
    if not brand_slug:
        return True

    compound = f"{brand_slug}|{model_key}"
    compound_raw = f"{brand_key}|{model_key}"

    if brand_slug in OLX_EMPTY_MODEL_TAXONOMY_BRANDS:
        return True
    if compound in OLX_FE_TEXT_MODELS or compound_raw in OLX_FE_TEXT_MODELS:
        return True
    if compound in OLX_FE_MODEL_REMAP or compound_raw in OLX_FE_MODEL_REMAP:
        return False
    if compound in _BRAND_MODEL_HAND or compound_raw in _BRAND_MODEL_HAND:
        return False

    # Не з FE-аудиту: лише якщо slug уже в відомому whitelist path
    known = OLX_KNOWN_MODEL_PATHS.get(brand_slug)
    if known is not None:
        if not known:
            return True
        resolved = _resolve_model_slug_unchecked(model_key, brand_slug=brand_slug, brand_key=brand_key)
        return resolved not in known

    # Марка взагалі не зі scrape — безпечніше text, ніж 404
    return True


def _resolve_model_slug_unchecked(model_key: str, *, brand_slug: str, brand_key: str) -> str:
    compound = f"{brand_slug}|{model_key}"
    if compound in BRAND_MODEL_TO_SLUG:
        return BRAND_MODEL_TO_SLUG[compound]
    compound_raw = f"{brand_key}|{model_key}"
    if compound_raw in BRAND_MODEL_TO_SLUG:
        return BRAND_MODEL_TO_SLUG[compound_raw]
    if model_key in MODEL_TO_SLUG:
        return MODEL_TO_SLUG[model_key]
    series_match = _SERIES_RE.match(model_key)
    if series_match and brand_slug == "bmw":
        return f"{series_match.group(1)}-serya"
    return slugify(model_key)


def resolve_olx_brand_slug(brand: str) -> str:
    key = _norm(brand)
    if key in BRAND_TO_SLUG:
        return BRAND_TO_SLUG[key]
    slug = slugify(brand)
    return slug or key.replace(" ", "-")


# Токен для /q-.../ (народне написання на OLX.ua; taxonomy-path лишається окремо)
OLX_TEXT_BRAND_TOKENS: dict[str, str] = {
    "mercedes-benz": "mersedes",
}

# Альтернативні написання для паралельного /q-.../ (написи в оголошеннях різняться)
OLX_TEXT_BRAND_VARIANTS: dict[str, tuple[str, ...]] = {
    "mercedes-benz": ("mersedes", "mercedes", "mercedes-benz", "мерседес"),
    "volkswagen": ("volkswagen", "vw", "фольксваген"),
    "bmw": ("bmw", "бмв"),
    "toyota": ("toyota", "тойота"),
    "hyundai": ("hyundai", "хюндай", "хендай"),
    "kia": ("kia", "кіа"),
    "nissan": ("nissan", "ніссан"),
    "ford": ("ford", "форд"),
    "skoda": ("skoda", "шкода"),
    "renault": ("renault", "рено"),
    "peugeot": ("peugeot", "пежо"),
    "citroen": ("citroen", "сітроен", "ситроен"),
    "opel": ("opel", "опель"),
    "mazda": ("mazda", "мазда"),
    "lexus": ("lexus", "лексус"),
    "audi": ("audi", "ауді", "ауди"),
    "chevrolet": ("chevrolet", "шевроле"),
    "mitsubishi": ("mitsubishi", "міцубісі"),
    "subaru": ("subaru", "субару"),
    "honda": ("honda", "хонда"),
    "volvo": ("volvo", "вольво"),
    "jeep": ("jeep", "джип"),
    "porsche": ("porsche", "порше"),
    "land-rover": ("land-rover", "land rover", "ленд ровер"),
}

# Скільки різних /q-/ запитів максимум на один пошук (включно з основним text)
MAX_OLX_TEXT_QUERY_VARIANTS = 4


def resolve_olx_text_brand_query(brand: str) -> str:
    """Текст у /q-{brand}/ — для Mercedes народне «mersedes», не mercedes-benz."""
    slug = resolve_olx_brand_slug(brand)
    return OLX_TEXT_BRAND_TOKENS.get(slug, slug)


def build_olx_text_query_variants(brand: str, model: str = "") -> list[str]:
    """Унікальні text_query для різних написань марки (+ модель)."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return []

    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    model_token = slugify(model) if model else ""

    tokens: list[str] = []
    if brand:
        primary = resolve_olx_text_brand_query(brand)
        if primary:
            tokens.append(primary)
        for alt in OLX_TEXT_BRAND_VARIANTS.get(brand_slug, ()):
            if alt and alt not in tokens:
                tokens.append(alt)
        if brand_slug and brand_slug not in tokens:
            tokens.append(brand_slug)

    out: list[str] = []
    seen: set[str] = set()
    for token in tokens or [""]:
        if brand and not token:
            continue
        if model_token and token:
            # Mercedes folk: mersedes-gla; цифрові (Zeekr 001) — також у q
            query = f"{token} {model_token}"
        elif model_token:
            query = model_token
        else:
            query = token
        key = query.casefold().replace(" ", "-")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(query)
        if len(out) >= MAX_OLX_TEXT_QUERY_VARIANTS:
            break
    return out


def resolve_olx_model_slug(model: str, *, brand: str = "") -> str:
    model_key = _norm(model)
    brand_key = _norm(brand)
    brand_slug = BRAND_TO_SLUG.get(brand_key, slugify(brand)) if brand else ""
    return _resolve_model_slug_unchecked(model_key, brand_slug=brand_slug, brand_key=brand_key)
