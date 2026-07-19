"""Ключові слова та аліаси марок/моделей для OLX, Telegram і пост-фільтрації.

Покриває latin, UA та RU написання з FE-каталогу (~87 марок / 1400+ моделей).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from app.core.text import norm_text
from app.services.search.fe_catalog import (
    _identity_tokens,
    unique_model_token_owner,
)
from app.services.olx.brand_slugs import (
    BRAND_TO_SLUG,
    MODEL_TO_SLUG,
    build_model_text_tokens,
    compose_olx_text_query,
    primary_model_text_token,
    resolve_olx_brand_slug,
    slugify,
)

MAX_TELEGRAM_KEYWORD_QUERIES = 4
MAX_SEARCH_KEYWORD_QUERIES = 10
TELEGRAM_SCAN_QUERY_PREFIX = "__scan__:"
TELEGRAM_HISTORY_SCAN_LIMIT = 500

# RU/UA написання марок (slug → варіанти). Доповнює BRAND_TO_SLUG.
BRAND_SLUG_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "acura": ("акура",),
    "alfa-romeo": ("альфа ромео", "альфа-ромео", "alfa romeo"),
    "aston-martin": ("астон мартин", "астон-мартин"),
    "audi": ("ауди", "ауді", "audi"),
    "baic": ("баик", "baic"),
    "bentley": ("бентли", "бентлі", "bentley"),
    "bmw": ("бмв", "bmw"),
    "buick": ("бьюик", "buick"),
    "byd": ("бид", "бйд", "byd"),
    "cadillac": ("кадиллак", "cadillac"),
    "changan": ("чанган", "changan"),
    "chery": ("чери", "chery", "чery"),
    "chevrolet": ("шевроле", "chevrolet", "chevy"),
    "chrysler": ("крайслер", "chrysler"),
    "citroen": ("ситроен", "сітроен", "citroen", "citroën"),
    "cupra": ("купра", "cupra"),
    "dacia": ("дачия", "дачія", "dacia"),
    "daewoo": ("дэу", "деу", "daewoo"),
    "daf": ("даф", "daf"),
    "dodge": ("додж", "dodge"),
    "dongfeng": ("dongfeng", "донгфенг"),
    "ds": ("ds", "дс"),
    "fiat": ("фиат", "фіат", "fiat"),
    "ford": ("форд", "ford"),
    "foton": ("foton", "фотон"),
    "gac": ("gac", "гац"),
    "geely": ("джили", "джилі", "geely", "gili"),
    "genesis": ("genesis", "дженesis", "генesis"),
    "gmc": ("gmc", "джиэмси"),
    "great-wall": ("great wall", "грейт волл", "gwm"),
    "haval": ("хавал", "haval"),
    "honda": ("хонда", "honda"),
    "hummer": ("hummer", "хаммер"),
    "hyundai": ("хендай", "хюндай", "хёндай", "hyundai"),
    "infiniti": ("инфинити", "інфініті", "infiniti"),
    "isuzu": ("isuzu", "исузу"),
    "iveco": ("iveco", "ивеко", "івеко"),
    "jac": ("jac", "джак"),
    "jaecoo": ("jaecoo", "джику", "джеку"),
    "jaguar": ("ягуар", "jaguar"),
    "jeep": ("джип", "jeep"),
    "jetour": ("jetour", "джетур"),
    "kia": ("киа", "кіа", "kia"),
    "lada": ("лада", "ваз", "lada"),
    "lamborghini": ("ламборгини", "lamborghini"),
    "lancia": ("lancia", "ланча"),
    "land-rover": ("land rover", "ленд ровер", "range rover", "рендж ровер", "лендровер"),
    "lexus": ("лексус", "lexus"),
    "li-auto": ("li auto", "li-auto", "lixiang", "li xiang", "ли авто"),
    "lifan": ("lifan", "лифан"),
    "lincoln": ("линкольн", "lincoln"),
    "lotus": ("lotus", "лотус"),
    "lucid": ("lucid", "люсид"),
    "man": ("man", "ман"),
    "maserati": ("maserati", "мазерати"),
    "mazda": ("мазда", "mazda"),
    "mclaren": ("mclaren", "макларен"),
    "mercedes-benz": (
        "mersedes",
        "mercedes",
        "mercedes-benz",
        "mercedes benz",
        "мерседес",
        "мерседес-бенц",
        "мерседес бенц",
        "мерс",
    ),
    "mg": ("mg", "эмджи"),
    "mini": ("mini", "міні", "мини"),
    "mitsubishi": ("митсубиси", "митсубиши", "міцубісі", "mitsubishi"),
    "nio": ("nio", "нио"),
    "nissan": ("нissan", "ніссан", "nissan"),
    "omoda": ("omoda", "омода"),
    "opel": ("опель", "opel"),
    "peugeot": ("пежо", "peugeot"),
    "polestar": ("polestar", "полстар"),
    "porsche": ("порше", "porsche"),
    "ram": ("ram", "рам"),
    "ravon": ("ravon", "равon"),
    "renault": ("рено", "renault"),
    "rivian": ("rivian", "ривиан"),
    "rover": ("rover", "ровер"),
    "saab": ("saab", "сааб"),
    "scania": ("scania", "скания", "сканія"),
    "seat": ("seat", "сеат"),
    "skoda": ("skoda", "шкода", "škoda"),
    "skywell": ("skywell", "скайвелл"),
    "smart": ("smart", "смарт"),
    "ssangyong": ("ssangyong", "ssang yong", "санг йонг", "сангйонг"),
    "subaru": ("субaru", "subaru"),
    "suzuki": ("suzuki", "сузуки", "сузукі"),
    "tesla": ("tesla", "тесла", "tesla motors"),
    "toyota": ("toyota", "тойота", "toyta"),
    "volkswagen": ("volkswagen", "vw", "фольксваген", "вольксваген", "volks"),
    "volvo": ("volvo", "вольво", "волво"),
    "xpeng": ("xpeng", "x peng", "xiao peng", "сяopeng"),
    "zaz": ("zaz", "заз"),
    "zeekr": ("zeekr", "зикр", "зікр", "зеекр"),
    "aito": ("aito", "айто"),
    "avatr": ("avatr", "авatr"),
    "deepal": ("deepal", "deepal"),
    "exeed": ("exeed", "exeed"),
    "foton": ("foton",),
    "hongqi": ("hongqi", "hong qi"),
    "hummer": ("hummer",),
    "leapmotor": ("leapmotor",),
    "ora": ("ora",),
    "seres": ("seres",),
    "tank": ("tank", "танк"),
    "vinfast": ("vinfast",),
    "voyah": ("voyah", "воя"),
    "wey": ("wey",),
    "lynk-and-co": ("lynk and co", "lynk&co", "lynk-and-co"),
}

# RU/UA варіанти популярних моделей (normalized model key → aliases)
MODEL_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "3 series": ("3 series", "3 серии", "3 серія", "3-seriya", "3seriya", "320", "330", "318"),
    "5 series": ("5 series", "5 серии", "5 серія", "520", "530", "525"),
    "7 series": ("7 series", "7 серии", "7 серія", "730", "740", "750"),
    "c-class": ("c-class", "c class", "c класс", "c-класс", "c клас", "c200", "c220", "c180"),
    "e-class": ("e-class", "e class", "e класс", "e-класс", "e клас", "e200", "e220", "e350"),
    "s-class": ("s-class", "s class", "s класс", "s-класс", "s500", "s350", "w222", "w223"),
    "a-class": ("a-class", "a class", "a класс", "a-класс"),
    "g-class": ("g-class", "g class", "g класс", "g-класс", "g63", "g500", "gelik", "гелик"),
    "m-class": ("m-class", "ml", "ml-class", "ml класс"),
    "glc": ("glc", "glc-class", "gl c"),
    "gle": ("gle", "gle-class"),
    "gla": ("gla", "gla-class"),
    "glb": ("glb", "glb-class"),
    "model s": ("model s", "model-s", "models", "модел s", "модель s", "model s plaid"),
    "model 3": (
        "model 3",
        "model-3",
        "model3",
        "модел 3",
        "модель 3",
    ),
    "model y": ("model y", "model-y", "modely", "модел y", "модель y", "tesla y", "тесла y"),
    "model x": ("model x", "model-x", "modelx", "модел x", "модель x", "tesla x", "тесла x"),
    "land cruiser prado": ("prado", "прадо", "land cruiser prado", "lc prado", "lcprado"),
    "rav4": ("rav4", "rav-4", "рав4", "раv4"),
    "camry": ("camry", "камри", "камри"),
    "corolla": ("corolla", "королла", "корола"),
    "passat": ("passat", "пасат", "passat b8", "passat b7"),
    "octavia": ("octavia", "октавия", "октавія"),
    "tiguan": ("tiguan", "тиguan", "тіguan"),
    "touareg": ("touareg", "туарег"),
    "golf": ("golf", "гольф"),
    "polo": ("polo", "поло"),
    "qashqai": ("qashqai", "кашкай", "qashkai"),
    "x-trail": ("x-trail", "xtrail", "икстрейл"),
    "sportage": ("sportage", "спортейдж", "спортаж"),
    "tucson": ("tucson", "тусон"),
    "sorento": ("sorento", "соренто"),
    "ceed": ("ceed", "сид", "сeed"),
    "macan": ("macan", "макan", "макан"),
    "cayenne": ("cayenne", "каен", "каенн"),
    "panamera": ("panamera", "panamera", "panamera"),
    "001": ("001", "zeekr 001", "зикр 001", "зікр 001", "зеекр 001"),
    "007": ("007", "zeekr 007", "зикр 007", "зікр 007", "зеекр 007"),
    "009": ("009", "zeekr 009", "зикр 009", "зікр 009", "зеекр 009"),
    "x": ("x", "zeekr x", "зикр x", "зікр x", "зеекр x"),
}


@lru_cache(maxsize=512)
def collect_brand_keyword_variants(brand: str) -> tuple[str, ...]:
    """Усі написання марки для keyword-пошуку та matching."""
    brand = (brand or "").strip()
    if not brand:
        return ()

    slug = resolve_olx_brand_slug(brand)
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = norm_text(token)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(token)

    add(brand)
    add(slug)
    add(brand.replace("-", " "))
    for alias in BRAND_SLUG_EXTRA_ALIASES.get(slug, ()):
        add(alias)
    for name, name_slug in BRAND_TO_SLUG.items():
        if name_slug == slug:
            add(name)
    return tuple(out)


@lru_cache(maxsize=4096)
def collect_model_keyword_variants(brand: str, model: str) -> tuple[str, ...]:
    """Усі написання моделі для keyword-пошуку та matching."""
    model = (model or "").strip()
    if not model:
        return ()

    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = norm_text(token)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(token)

    add(model)
    add(model.replace("-", " "))
    for token in build_model_text_tokens(model, brand_slug):
        add(token)
    add(primary_model_text_token(model, brand_slug))

    model_key = norm_text(model)
    for extra in MODEL_EXTRA_ALIASES.get(model_key, ()):
        add(extra)

    target_slug = slugify(primary_model_text_token(model, brand_slug))
    for alias, alias_slug in MODEL_TO_SLUG.items():
        if alias_slug == target_slug or alias_slug == slugify(model):
            add(alias)

    out.extend(_generated_model_ru_variants(model))
    out.extend(_generated_short_model_variants(brand, model))
    deduped: list[str] = []
    seen.clear()
    for token in out:
        key = norm_text(token)
        if key and key not in seen:
            seen.add(key)
            deduped.append(token)
    return tuple(deduped)


def _generated_model_ru_variants(model: str) -> list[str]:
    """RU/UA/latin варіанти для типових патернів назв моделей (усі марки)."""
    out: list[str] = []
    base = model.strip()
    mk = norm_text(base)

    class_m = re.match(r"^([A-Za-z])-Class\b", base, re.IGNORECASE)
    if class_m:
        letter = class_m.group(1).lower()
        out.extend(
            [
                f"{letter}-class",
                f"{letter} class",
                f"{letter} класс",
                f"{letter}-класс",
                f"{letter} клас",
                f"{letter}класс",
                f"{letter}-клас",
            ]
        )

    series_m = re.match(r"^(\d+)\s+Series\b", base, re.IGNORECASE)
    if series_m:
        num = series_m.group(1)
        out.extend(
            [
                f"{num} series",
                f"{num} серии",
                f"{num} серія",
                f"{num}-series",
                f"{num}seriya",
            ]
        )

    if re.search(r"model\s+[sx3y]", base, re.IGNORECASE):
        for cyr in ("модел", "модель"):
            rest = re.sub(r"^model\s+", "", base, flags=re.IGNORECASE)
            out.append(f"{cyr} {rest}")

    # ID.3 / ID.4 / e-tron / C-HR / T-Roc
    id_m = re.match(r"^id\.?\s*(\d+)$", base, re.IGNORECASE)
    if id_m:
        num = id_m.group(1)
        out.extend([f"id{num}", f"id {num}", f"id.{num}"])

    if re.search(r"e-tron|e tron", base, re.IGNORECASE):
        out.append(re.sub(r"\s+", " ", base, flags=re.IGNORECASE).lower())
        out.append(re.sub(r"[\s\-]+", "", base, flags=re.IGNORECASE).lower())

    hyphen_word = re.match(r"^([A-Za-z])-([A-Za-z0-9]+)$", base)
    if hyphen_word:
        a, b = hyphen_word.group(1).lower(), hyphen_word.group(2).lower()
        out.extend([f"{a}{b}", f"{a} {b}", f"{a}-{b}"])

    words = [w for w in re.split(r"[\s\-./]+", base) if w]
    if len(words) >= 2:
        out.append(words[-1])
        out.append(" ".join(words[-2:]).lower())
        if len(words[-1]) >= 4:
            out.append(words[-1].lower())

    alnum = re.sub(r"[\s\-._]+", "", base.lower())
    if alnum and alnum != base.lower():
        out.append(alnum)

    if mk.startswith("land cruiser"):
        out.extend(["lc", "land cruiser", "lc prado", "land cruiser prado"])

    if mk.startswith("range rover"):
        out.append("rr")

    return out


# Занадто короткі / шумні токени не годяться для SQL ILIKE і standalone match
_SQL_SKIP_TOKENS = frozenset({"model", "models", "s", "x", "y", "3"})


def _model_core_tokens(brand: str, model: str) -> tuple[str, ...]:
    """Компактні токени моделі для brand+model shorthand (усі марки)."""
    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    base = model.strip()
    mk = norm_text(base)
    tokens: list[str] = []

    def add(raw: str) -> None:
        t = (raw or "").strip()
        if t and norm_text(t) not in {norm_text(x) for x in tokens}:
            tokens.append(t)

    add(base)
    add(base.lower())
    add(primary_model_text_token(model, brand_slug).replace("-", " "))
    compact = re.sub(r"[\s\-._]+", "", base.lower())
    if compact:
        add(compact)

    for token in _identity_tokens(model):
        add(token)

    tesla_m = re.match(r"^model\s+([3sxy])$", mk)
    if tesla_m:
        add(tesla_m.group(1))
        add(f"model {tesla_m.group(1)}")

    series_m = re.match(r"^(\d+)\s+series$", mk)
    if series_m:
        add(series_m.group(1))

    class_m = re.match(r"^([a-z])-class$", mk)
    if class_m:
        add(class_m.group(1))

    id_m = re.match(r"^id\.?\s*(\d+)$", mk)
    if id_m:
        add(f"id{id_m.group(1)}")
        add(f"id {id_m.group(1)}")

    letter_num = re.fullmatch(r"[a-z]{1,3}\d+[a-z0-9]*", compact)
    if letter_num:
        add(compact)

    return tuple(tokens[:16])


def _generated_short_model_variants(brand: str, model: str) -> list[str]:
    """Colloquial форми для будь-якої марки: «toyota prado», «vw golf», «ауди a4» …"""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not model:
        return []

    out: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = norm_text(token)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(token)

    brand_tokens = list(collect_brand_keyword_variants(brand)) if brand else []
    cores = _model_core_tokens(brand, model)

    for core in cores:
        if not core:
            continue
        core_key = norm_text(core)
        # Голі «3» / «s» / «x» / «y» ловлять рік, ціну, пробіг — лише з маркою.
        standalone_ok = core_key not in _SQL_SKIP_TOKENS and not (
            len(core_key) <= 1 or (core_key.isdigit() and len(core_key) <= 2)
        )
        if standalone_ok:
            add(core)
        if not brand_tokens:
            continue
        for bt in brand_tokens:
            if len(norm_text(bt)) < 2:
                continue
            add(f"{bt} {core}")
            if re.fullmatch(r"\d{3}", core_key) or re.fullmatch(r"[a-z0-9]{2,4}", core_key):
                add(f"{bt}{core}".replace(" ", ""))

    return out


def _allows_distinctive_model_without_brand(brand: str, model: str) -> bool:
    """Модель у FE унікальна для марки → brand може не бути в тексті."""
    slug = resolve_olx_brand_slug(brand) if brand else ""
    if not slug or not model:
        return False

    index = unique_model_token_owner()
    for token in _identity_tokens(model):
        if index.get(norm_text(token)) == slug:
            return True

    if slug == "tesla" and re.match(r"^model\s+[3sxy]$", norm_text(model)):
        return True
    return False


def _brand_shorthand_variants(brand: str, model: str) -> tuple[str, ...]:
    """Варіанти «brand + core» для всіх марок."""
    return tuple(
        v
        for v in _generated_short_model_variants(brand, model)
        if " " in v
        and any(
            norm_text(bt) in norm_text(v)
            for bt in collect_brand_keyword_variants(brand)
        )
    )


def _regex_model_patterns(brand: str, model: str) -> tuple[str, ...]:
    """Regex для colloquial написань — усі марки."""
    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    mk = norm_text(model)
    patterns: list[str] = []
    seen: set[str] = set()

    def add(pat: str) -> None:
        if pat and pat not in seen:
            seen.add(pat)
            patterns.append(pat)

    tesla_m = re.match(r"^model\s+([3sxy])$", mk)
    if tesla_m:
        token = re.escape(tesla_m.group(1))
        for pat in (
            rf"\bmodel[\s\-]?{token}\b",
            rf"\bмодел[\s\-]?{token}\b",
            rf"\bмодель[\s\-]?{token}\b",
            rf"\btesla[\s\-]?{token}\b",
            rf"\bтесла[\s\-]?{token}\b",
        ):
            add(pat)

    series_m = re.match(r"^(\d+)\s+series$", mk)
    if series_m:
        num = re.escape(series_m.group(1))
        add(rf"\b{num}[\s\-]?series\b")
        add(rf"\b{num}[\s\-]?ser(?:ii|iya|ies|і)\b")

    class_m = re.match(r"^([a-z])-class$", mk)
    if class_m:
        letter = re.escape(class_m.group(1))
        add(rf"\b{letter}[\s\-]?class\b")
        add(rf"\b{letter}[\s\-]?клас")

    id_m = re.match(r"^id\.?\s*(\d+)$", mk)
    if id_m:
        num = re.escape(id_m.group(1))
        add(rf"\bid[\s\-.]?{num}\b")

    for core in _model_core_tokens(brand, model):
        c = norm_text(core)
        if len(c) < 2:
            continue
        esc = re.escape(c)
        if len(c) <= 3 and c.isalpha():
            add(rf"(?<![a-zа-яёіїє0-9]){esc}(?![a-zа-яёіїє0-9])")
        elif " " in c or "-" in c:
            add(esc.replace(r"\ ", r"[\s\-]?").replace(r"\-", r"[\s\-]?"))

    if brand:
        for bt in collect_brand_keyword_variants(brand):
            b = norm_text(bt)
            if len(b) < 2:
                continue
            b_esc = re.escape(b)
            for core in _model_core_tokens(brand, model):
                c = norm_text(core)
                if len(c) < 1:
                    continue
                if c.isdigit() and len(c) == 1:
                    continue
                c_esc = re.escape(c)
                add(rf"\b{b_esc}[\s\-./]{{0,3}}{c_esc}\b")
                if len(c) <= 4 and re.fullmatch(r"[a-z0-9]+", c):
                    add(rf"\b{b_esc}[\s\-./]{{0,3}}{c_esc}(?:[\s\-./]|$|\d)")

    return tuple(patterns[:40])


def _regex_model_match(hay: str, brand: str, model: str) -> bool:
    for pattern in _regex_model_patterns(brand, model):
        if re.search(pattern, hay, re.IGNORECASE):
            return True
    return False


def build_search_keyword_queries(
    brand: str,
    model: str = "",
    *,
    max_queries: int = MAX_SEARCH_KEYWORD_QUERIES,
) -> list[str]:
    """Комбінації brand+model для Telethon / OLX / matching (latin + RU)."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return []

    olx_primary = compose_olx_text_query(brand, model) if brand else ""
    brand_tokens = list(collect_brand_keyword_variants(brand)) if brand else []
    model_tokens = list(collect_model_keyword_variants(brand, model)) if model else [""]

    seen: set[str] = set()
    out: list[str] = []

    def add(query: str) -> None:
        q = (query or "").strip()
        if not q:
            return
        key = norm_text(q)
        if key in seen:
            return
        seen.add(key)
        out.append(q)

    if olx_primary:
        add(olx_primary)
    for bt in brand_tokens:
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
    return out[: max(1, max_queries)]


def filter_sql_search_tokens(variants: tuple[str, ...] | list[str], *, limit: int = 6) -> tuple[str, ...]:
    """Безпечні ключі для Telegram SQL ILIKE (без «s», «models» тощо)."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in variants:
        token = (raw or "").strip()
        if not token:
            continue
        key = norm_text(token)
        if not key or key in seen or key in _SQL_SKIP_TOKENS:
            continue
        if len(key) <= 2 and not any(ch.isdigit() for ch in key):
            continue
        seen.add(key)
        out.append(token)
        if len(out) >= limit:
            break
    return tuple(out)


def build_telegram_keyword_queries(filters) -> list[str]:
    """Deprecated: один scan-job на канал; лишено для тестів."""
    brand = (getattr(filters, "brand", None) or "").strip()
    model = (getattr(filters, "model", None) or "").strip()
    if not brand and not model:
        return []
    return [encode_telegram_scan_job(brand, model)]


def encode_telegram_scan_job(brand: str, model: str = "") -> str:
    """Payload для keyword_search_queue: повний scan історії + variant matching."""
    payload = {
        "brand": (brand or "").strip(),
        "model": (model or "").strip(),
    }
    return TELEGRAM_SCAN_QUERY_PREFIX + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )


def decode_telegram_scan_job(query: str) -> dict[str, str] | None:
    q = (query or "").strip()
    if not q.startswith(TELEGRAM_SCAN_QUERY_PREFIX):
        return None
    try:
        data = json.loads(q[len(TELEGRAM_SCAN_QUERY_PREFIX) :])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    brand = str(data.get("brand") or "").strip()
    if not brand:
        return None
    return {"brand": brand, "model": str(data.get("model") or "").strip()}


def _haystacks_for_match(text: str) -> tuple[str, ...]:
    """Raw + homoglyph-normalized (ТЕSLA → TESLA), без дублікатів."""
    raw = text or ""
    if not raw:
        return ()
    try:
        from app.services.olx.parser import _normalize_title_for_match

        alt = _normalize_title_for_match(raw)
    except ImportError:
        alt = raw
    if alt != raw:
        return (raw, alt)
    return (raw,)


def message_matches_search_filters(text: str, brand: str, model: str = "") -> bool:
    """Чи підходить текст повідомлення за brand/model (усі keyword-варіанти)."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return False
    for hay in _haystacks_for_match(text):
        if brand and not text_matches_brand_filter(hay, brand, model=model):
            continue
        if model and not text_matches_model_filter(hay, model, brand=brand):
            continue
        return True
    return False


def _variant_in_haystack(variant: str, hay: str) -> bool:
    v = norm_text(variant)
    if not v or not hay:
        return False
    # Шумні однолітерні/цифрові токени без контексту марки.
    if v in _SQL_SKIP_TOKENS and " " not in (variant or "").strip().lower():
        return False
    if len(v) <= 2 and v.isalpha():
        return bool(
            re.search(
                rf"(?<![a-zа-яёіїє0-9]){re.escape(v)}(?![a-zа-яёіїє0-9])",
                hay,
            )
        )
    if v.isdigit() and len(v) <= 2:
        return bool(
            re.search(
                rf"(?<![a-zа-яёіїє0-9]){re.escape(v)}(?![a-zа-яёіїє0-9])",
                hay,
            )
        )
    return v in hay


def text_matches_brand_filter(haystack: str, brand: str, *, model: str = "") -> bool:
    if not haystack or not brand:
        return True
    for raw in _haystacks_for_match(haystack):
        hay = norm_text(raw)
        if not hay:
            continue
        for variant in collect_brand_keyword_variants(brand):
            if _variant_in_haystack(variant, hay):
                return True
        if model:
            for shorthand in _brand_shorthand_variants(brand, model):
                if _variant_in_haystack(shorthand, hay):
                    return True
            if _allows_distinctive_model_without_brand(brand, model) and text_matches_model_filter(
                raw, model, brand=brand
            ):
                return True
    return False


def text_matches_model_filter(haystack: str, model: str, *, brand: str = "") -> bool:
    if not haystack or not model:
        return True
    for raw in _haystacks_for_match(haystack):
        hay = norm_text(raw)
        if not hay:
            continue
        for variant in collect_model_keyword_variants(brand, model):
            if _variant_in_haystack(variant, hay):
                return True
        if norm_text(model) in hay:
            return True
        if _regex_model_match(hay, brand, model):
            return True
        from app.services.olx.parser import _title_has_model

        if _title_has_model(hay, model, brand=brand) or _title_has_model(raw, model, brand=brand):
            return True
    return False
