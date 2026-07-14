from __future__ import annotations

import re


from app.core.text import norm_text as _norm


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
    "rav4": "rav4",
    "рав4": "rav4",
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

# Марка + модель → slug моделі на OLX
BRAND_MODEL_TO_SLUG: dict[str, str] = {
    "bmw|1 series": "1-seriya",
    "bmw|2 series": "2-seriya",
    "bmw|3 series": "3-seriya",
    "bmw|4 series": "4-seriya",
    "bmw|5 series": "5-seriya",
    "bmw|6 series": "6-seriya",
    "bmw|7 series": "7-seriya",
    "bmw|8 series": "8-seriya",
    "bmw|3 series gt": "3-seriya",
    "bmw|5 series gt": "5-seriya",
    "бмв|3 series": "3-seriya",
    "бмв|5 series": "5-seriya",
    "mercedes-benz|c-class": "c-klass",
    "mercedes-benz|e-class": "e-klass",
    "mercedes-benz|s-class": "s-klass",
    "mercedes-benz|g-class": "g-klass",
    "mercedes-benz|glc": "glc",
    "mercedes-benz|gle": "gle",
    "mercedes-benz|gls": "gls",
    "mercedes-benz|a-class": "a-klass",
    "mercedes-benz|b-class": "b-klass",
    "мерседес|c-class": "c-klass",
    "мерседес|e-class": "e-klass",
    "audi|a4 allroad": "a4-allroad",
    "audi|a6 allroad": "a6-allroad",
    "audi|e-tron gt": "e-tron-gt",
    "audi|q4 e-tron": "q4-e-tron",
    "volkswagen|golf": "golf",
    "volkswagen|passat": "passat",
    "toyota|rav4": "rav4",
    "toyota|land cruiser": "land-cruiser",
    "toyota|land cruiser prado": "land-cruiser-prado",
    "toyota|prado": "land-cruiser-prado",
}

_SERIES_RE = re.compile(
    r"^(\d+)\s*(?:series|серії|серии|серія|серия|seriya|seriya)?$",
    re.IGNORECASE,
)


# Slug у path OLX, які дають 404 (перевірено live 2026-07). Шукаємо через /q-.../
OLX_TEXT_SEARCH_SLUGS = frozenset(
    {
        "aito",
        "avatr",
        "baic",
        "bugatti",
        "byd",
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
        "byd",
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


def resolve_olx_brand_slug(brand: str) -> str:
    key = _norm(brand)
    if key in BRAND_TO_SLUG:
        return BRAND_TO_SLUG[key]
    slug = slugify(brand)
    return slug or key.replace(" ", "-")


def resolve_olx_model_slug(model: str, *, brand: str = "") -> str:
    model_key = _norm(model)
    brand_key = _norm(brand)
    brand_slug = BRAND_TO_SLUG.get(brand_key, slugify(brand)) if brand else ""

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
        return f"{series_match.group(1)}-seriya"

    return slugify(model)
