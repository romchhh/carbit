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
    "leap": "leapmotor",
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
    "lynk&co": "lynk-and-co",
    "wey": "wey",
    "xiaomi": "xiaomi",
    "huawei": "huawei",
    "denza": "denza",
    "yangwang": "yangwang",
    "yang wang": "yangwang",
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
    # Russian / folk (extended)
    "альфа ромео": "alfa-romeo",
    "альфа-ромео": "alfa-romeo",
    "астон мартин": "aston-martin",
    "баик": "baic",
    "бьюик": "buick",
    "бид": "byd",
    "кадиллак": "cadillac",
    "чанган": "changan",
    "чери": "chery",
    "купра": "cupra",
    "дачия": "dacia",
    "донгфенг": "dongfeng",
    "ламборгини": "lamborghini",
    "ланча": "lancia",
    "рендж ровер": "land-rover",
    "ли авто": "li-auto",
    "лифан": "lifan",
    "линкольн": "lincoln",
    "лотус": "lotus",
    "ман": "man",
    "мазерати": "maserati",
    "макларен": "mclaren",
    "митсубиши": "mitsubishi",
    "нио": "nio",
    "полстар": "polestar",
    "рам": "ram",
    "ровер": "rover",
    "сааб": "saab",
    "скания": "scania",
    "сеат": "seat",
    "санг йонг": "ssangyong",
    "сангйонг": "ssangyong",
    "сузуки": "suzuki",
    "сузукі": "suzuki",
    "грейт волл": "great-wall",
    "хавал": "haval",
    "хаммер": "hummer",
    "исузу": "isuzu",
    "джак": "jac",
    "джеку": "jaecoo",
    "генesis": "genesis",
    "дженesis": "genesis",
    "вольво": "volvo",
    "вольксваген": "volkswagen",
    "гелик": "mercedes-benz",
    "мерс": "mercedes-benz",
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
    "мерседес-бенц|c-class": "c-seriya",
    "мерседес-бенц|e-class": "e-seriya",
    "мерседес-бенц|s-class": "s-seriya",
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
        "denza",
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
        "huawei",
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
        "xiaomi",
        "xpeng",
        "yangwang",
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
        "avatr",
        "xiaomi",
        "huawei",
        "aito",
        "hongqi",
        "leapmotor",
        "denza",
        "yangwang",
        "deepal",
        "seres",
        "ora",
        "tank",
        "exeed",
        "wey",
        "vinfast",
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
    "nissan": ("nissan", "ніссан", "нissan"),
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
    "tesla": ("tesla", "тесла", "tesla motors"),
    "byd": ("byd", "бід", "бйд"),
    "geely": ("geely", "джилі", "gili"),
    "zeekr": ("zeekr", "зікр", "зикр", "зеекр"),
    "chery": ("chery", "чері"),
    "haval": ("haval", "хaval"),
    "genesis": ("genesis", "дженesis", "генesis"),
    "infiniti": ("infiniti", "інфініті", "инфинити"),
    "dodge": ("dodge", "додж"),
    "chrysler": ("chrysler", "крайслер"),
    "fiat": ("fiat", "фіат", "фиат"),
    "jaguar": ("jaguar", "ягуар"),
    "bentley": ("bentley", "бентлі", "бентли"),
    "mini": ("mini", "міні", "мини"),
    "smart": ("smart", "смарт"),
    "ssangyong": ("ssangyong", "ssang yong", "санг йонг"),
    "daewoo": ("daewoo", "деву", "дэу"),
    "lada": ("lada", "лада", "ваз"),
    "zaz": ("zaz", "заз"),
    "acura": ("acura", "акура"),
}

# Скільки різних /q-/ запитів максимум на один пошук (включно з основним text)
MAX_OLX_TEXT_QUERY_VARIANTS = 6


def resolve_olx_text_brand_query(brand: str) -> str:
    """Текст у /q-{brand}/ — для Mercedes народне «mersedes», не mercedes-benz."""
    slug = resolve_olx_brand_slug(brand)
    return OLX_TEXT_BRAND_TOKENS.get(slug, slug)


def _collect_brand_text_tokens(brand: str) -> list[str]:
    """Усі написання марки для /q-/ (latin, кирилиця, slug, folk)."""
    brand_slug = resolve_olx_brand_slug(brand)
    tokens: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = token.casefold().replace(" ", "-")
        if key in seen:
            return
        seen.add(key)
        tokens.append(token)

    add(resolve_olx_text_brand_query(brand))
    for alt in OLX_TEXT_BRAND_VARIANTS.get(brand_slug, ()):
        add(alt)
    add(brand_slug)
    try:
        from app.services.search.brand_model_keywords import BRAND_SLUG_EXTRA_ALIASES

        for alias in BRAND_SLUG_EXTRA_ALIASES.get(brand_slug, ()):
            add(alias)
    except ImportError:
        pass
    for name, slug in BRAND_TO_SLUG.items():
        if slug == brand_slug:
            add(name)
    return tokens


def build_model_text_tokens(model: str, brand_slug: str = "") -> list[str]:
    """Варіанти моделі для /q-brand-model/ та пост-фільтра заголовків."""
    model = (model or "").strip()
    if not model:
        return []

    out: list[str] = []
    seen: set[str] = set()

    def push(token: str) -> None:
        t = (token or "").strip().lower()
        if not t:
            return
        key = t.replace(" ", "-")
        if key in seen:
            return
        seen.add(key)
        out.append(t)

    slug = slugify(model)
    base = model.lower()
    push(slug)
    push(base)
    push(base.replace(" ", "-"))
    push(base.replace("-", " "))
    push(re.sub(r"[\s\-_]+", "", base))

    model_word = re.fullmatch(r"model\s+([a-z0-9]+)", base, re.IGNORECASE)
    if model_word:
        letter = model_word.group(1).lower()
        for tok in (letter, f"model{letter}", f"model-{letter}", f"model {letter}"):
            push(tok)
        for cyr in ("модел", "модель"):
            push(f"{cyr} {letter}")
            push(f"{cyr}-{letter}")

    if re.match(r"model\s+", base, re.IGNORECASE):
        rest = re.sub(r"^model\s+", "", base, flags=re.IGNORECASE)
        for cyr in ("модел", "модель"):
            push(f"{cyr} {rest}")
            push(slugify(f"{cyr} {rest}"))

    parts = re.split(r"[\s\-/]+", base)
    if len(parts) >= 2:
        tail = parts[-1]
        push(tail)
        push(f"{parts[-2]}-{tail}")
        if len(parts) >= 3:
            push(f"{parts[-2]} {tail}")

    return out


def primary_model_text_token(model: str, brand_slug: str = "") -> str:
    """Найкращий токен моделі для primary /q-brand-model/ (не надто короткий)."""
    tokens = build_model_text_tokens(model, brand_slug)
    if not tokens:
        return slugify(model)

    base = model.lower()
    parts = re.split(r"[\s\-/]+", base)
    if len(parts) >= 3 and parts[-1] in tokens:
        return parts[-1]

    slug = slugify(model)
    if slug in tokens:
        return slug

    if brand_slug == "tesla" and re.fullmatch(r"model\s+\S+", model.strip(), re.IGNORECASE):
        for token in tokens:
            if token.startswith("model"):
                return token

    if re.search(r"[\s\-/]", base):
        for token in tokens:
            if " " in token or "-" in token:
                return token

    return tokens[0]


def _canonical_olx_model_token(model: str, brand_path: str = "") -> str:
    """Канонічний текст моделі для одного OLX /q-/ (пробіли, не slug)."""
    model = (model or "").strip()
    if not model:
        return ""
    if re.fullmatch(r"\d+[a-z]?", model, re.IGNORECASE):
        return model
    token = primary_model_text_token(model, brand_path)
    if token:
        return token.replace("-", " ").strip()
    return model.replace("-", " ").strip()


def compose_olx_text_query(brand: str, model: str = "") -> str:
    """Єдиний канонічний /q-/ запит (напр. «tesla model s»); аліаси — у пост-фільтрі."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return ""

    brand_q = resolve_olx_text_brand_query(brand) if brand else ""
    brand_path = resolve_olx_brand_slug(brand) if brand else ""

    if brand_q and model:
        model_q = _canonical_olx_model_token(model, brand_path)
        if model_q:
            return f"{brand_q} {model_q}".strip()
    if brand_q:
        return brand_q
    if model:
        return _canonical_olx_model_token(model, brand_path) or model
    return brand


def build_olx_text_query_variants(
    brand: str,
    model: str = "",
    *,
    max_queries: int | None = None,
) -> list[str]:
    """Унікальні text_query: комбінації написань марки × моделі."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return []

    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    brand_tokens = _collect_brand_text_tokens(brand) if brand else []
    model_tokens = build_model_text_tokens(model, brand_slug) if model else [""]

    out: list[str] = []
    seen: set[str] = set()

    def add(query: str) -> None:
        q = (query or "").strip()
        if not q:
            return
        key = q.casefold().replace(" ", "-")
        if key in seen:
            return
        seen.add(key)
        out.append(q)

    for bt in brand_tokens or [""]:
        if brand and not bt:
            continue
        for mt in model_tokens:
            if bt and mt:
                add(f"{bt} {mt}")
            elif bt:
                add(bt)
            elif mt:
                add(mt)

    if model:
        for bt in brand_tokens:
            add(bt)

    limit = max_queries if max_queries is not None else MAX_OLX_TEXT_QUERY_VARIANTS
    return out[: max(1, limit)]


def resolve_olx_model_slug(model: str, *, brand: str = "") -> str:
    model_key = _norm(model)
    brand_key = _norm(brand)
    brand_slug = BRAND_TO_SLUG.get(brand_key, slugify(brand)) if brand else ""
    return _resolve_model_slug_unchecked(model_key, brand_slug=brand_slug, brand_key=brand_key)
