from __future__ import annotations

BASE_URL = "https://www.olx.ua"
CATEGORY_PATH = "/uk/transport/legkovye-avtomobili"
# category_id для /api/v1/offers/ (Легкові автомобілі)
CARS_CATEGORY_ID = 108
OFFERS_API_PATH = "/api/v1/offers/"
OFFERS_API_LIMIT = 40
# Орієнтовна кількість карток на HTML-сторінці OLX
OLX_RESULTS_PER_PAGE = 40
# Скільки сторінок OLX максимум обходити за один пошук (live / моніторинг)
# Після API-first + серверних фільтрів 1–2 сторінки достатньо для швидкого live.
OLX_MAX_SCAN_PAGES = 2
# Для великого пулу (live search «усі джерела»)
OLX_POOL_MAX_SCAN_PAGES = 2
# Live-pool: скільки оголошень максимум тягнути з OLX
OLX_LIVE_POOL_CAP_WITH_BRAND = 80
OLX_LIVE_POOL_CAP_NO_BRAND = 40

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

REQUEST_TIMEOUT = 15.0
MIN_DELAY = 0.3
MAX_DELAY = 0.8
MAX_RETRIES = 2
# 5xx OLX/gateway — короткі ретраї (раніше лише 403/429)
RETRYABLE_STATUS = frozenset({403, 429, 502, 503, 504})

# Значення search[filter_enum_fuel_type] / API filter_enum_fuel_type (кат. 108)
FUEL_MAP = {
    "petrol": "542",
    "diesel": "543",
    "gas": "gas",
    "electric": "electro",
    "hybrid": "hybrid",
}

# search[filter_enum_transmission_type] (кат. 108)
TRANSMISSION_MAP = {
    "manual": "545",
    "automatic": "546",
    "variator": "547",
    # tiptronic як окремий enum; robot — лише пост-фільтр
    "tiptronic": "tip-tronic",
}

# search[filter_enum_drive_type]
DRIVETRAIN_MAP = {
    "awd": "full",
    "fwd": "front",
    "rwd": "back",
}

# search[filter_enum_color] — id з OLX
COLOR_NAME_TO_ENUM: dict[str, str] = {
    "білий": "1",
    "чорний": "2",
    "синій": "3",
    "сірий": "4",
    "срібний": "5",
    "червоний": "6",
    "зелений": "7",
    "помаранчевий": "8",
    "бежевий": "10",
    "жовтий": "15",
    "коричневий": "18",
    "фіолетовий": "24",
}

# search[filter_enum_car_body]
BODY_NAME_TO_ENUM: dict[str, str] = {
    "седан": "sedan",
    "універсал": "estate-car",
    "хетчбек": "hatchback",
    "хэтчбек": "hatchback",
    "купе": "coupe",
    "мінівен": "minibus",
    "минівэн": "minibus",
    "позашляховик": "off-road-vehicle",
    "кросовер": "off-road-vehicle",
    "пікап": "pickup",
    "ліфтбек": "liftback",
    "кабріолет": "cabriolet",
    "лімузин": "limo",
}

# search[filter_enum_car_from] — «авто пригнано з»
CAR_FROM_USA = "usa"

# search[filter_enum_condition] (стан авто, не new/used)
CONDITION_ENUM_NOT_BIT = "not-bit"
CONDITION_ENUM_AFTER_ACCIDENT = "after-an-accident"
CONDITION_ENUM_FIRST_OWNER = "first-owner"

# OLX region_id для областей (API + search[region_id])
# Перевірено live: Луганської немає в geo OLX.
REGION_TO_OLX_REGION_ID: dict[str, int] = {
    "сумська область": 1,
    "сумська": 1,
    "херсонська область": 3,
    "херсонська": 3,
    "донецька область": 4,
    "донецька": 4,
    "львівська область": 5,
    "львівська": 5,
    "житомирська область": 6,
    "житомирська": 6,
    "кіровоградська область": 7,
    "кіровоградська": 7,
    "харківська область": 8,
    "харківська": 8,
    "одеська область": 9,
    "одеська": 9,
    "закарпатська область": 10,
    "закарпатська": 10,
    "тернопільська область": 11,
    "тернопільська": 11,
    "черкаська область": 12,
    "черкаська": 12,
    "івано-франківська область": 13,
    "івано-франківська": 13,
    "рівненська область": 14,
    "рівненська": 14,
    "полтавська область": 15,
    "полтавська": 15,
    "запорізька область": 17,
    "запорізька": 17,
    "чернівецька область": 18,
    "чернівецька": 18,
    "миколаївська область": 19,
    "миколаївська": 19,
    "хмельницька область": 20,
    "хмельницька": 20,
    "дніпропетровська область": 21,
    "дніпропетровська": 21,
    "волинська область": 22,
    "волинська": 22,
    "чернігівська область": 23,
    "чернігівська": 23,
    "вінницька область": 24,
    "вінницька": 24,
    "київська область": 25,
    "київська": 25,
}
# м. Київ — окремий city_id (API); HTML — /q-kyiv/ (search[city_id] ігнорується)
OLX_KYIV_CITY_ID = 268
KYIV_REGION_KEYS = frozenset({"м. київ", "київ", "киев", "kyiv", "kiev"})

FUEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "petrol": ("бензин",),
    "diesel": ("дизел",),
    "gas": ("газ", "gas"),
    "electric": ("електр", "electric"),
    "hybrid": ("гібрид", "hybrid"),
}

TRANSMISSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "manual": ("механ", "manual"),
    "automatic": ("автомат", "automatic", "tiptronic", "типтрон"),
    "robot": ("робот", "robot"),
    "variator": ("варіатор", "variator", "cvt"),
}

# Українські назви з фільтрів Carbit → OLX enum keys
FUEL_NAME_TO_KEY: dict[str, str] = {
    "бензин": "petrol",
    "дизель": "diesel",
    "газ": "gas",
    "газ-бензин": "gas",
    "гібрид": "hybrid",
    "електро": "electric",
}

TRANSMISSION_NAME_TO_KEY: dict[str, str] = {
    "механіка": "manual",
    "ручна": "manual",
    "автомат": "automatic",
    "типтронік": "automatic",
    "робот": "robot",
    "варіатор": "variator",
}

CATEGORY_TO_CONDITION: dict[str, str] = {
    "used": "used",
    "new": "new",
    # OLX немає окремого «під пригон» — далі пост-фільтр за текстом.
    "import": "used",
}

DRIVETRAIN_NAME_TO_TOKEN: dict[str, str] = {
    "передній": "fwd",
    "задній": "rwd",
    "повний": "awd",
}

# Токени з фільтра → ключові слова в тексті/specs OLX (не «awd» у «Повний»).
DRIVETRAIN_TOKEN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fwd": ("перед", "fwd", "front"),
    "rwd": ("задн", "rwd", "rear"),
    "awd": ("повн", "awd", "4wd", "4x4", "all-wheel", "full"),
}


def drivetrain_token_matches(token: str, haystack: str) -> bool:
    text = (haystack or "").lower()
    if not text:
        return False
    key = (token or "").strip().lower()
    keywords = DRIVETRAIN_TOKEN_KEYWORDS.get(key, (key,))
    return any(kw in text for kw in keywords if kw)

COLOR_NAME_TO_TOKEN: dict[str, str] = {
    "білий": "біл",
    "чорний": "чорн",
    "сірий": "сір",
    "срібний": "сріб",
    "синій": "син",
    "червоний": "червон",
    "зелений": "зелен",
    "жовтий": "жовт",
    "помаранчевий": "помаранч",
    "коричневий": "коричн",
    "бежевий": "беж",
    "фіолетовий": "фіолет",
}

# Fallback /q-…/ лише для регіонів без OLX region_id (решта → search[region_id]).
REGION_TO_CITY_QUERY: dict[str, str] = {
    "луганська область": "луганська-область",
    "луганська": "луганська-область",
}

MODEL_SLUG_ALIASES: dict[str, str] = {
    "3 series": "3-serya",
    "5 series": "5-serya",
    "7 series": "7-serya",
    "1 series": "1-serya",
    "2 series": "2-serya",
    "4 series": "4-serya",
    "6 series": "6-serya",
    "8 series": "8-serya",
    "x5": "x5",
    "x3": "x3",
    "passat": "passat",
    "octavia": "octavia",
    "camry": "camry",
    "rav4": "rav-4",
    "rav-4": "rav-4",
}
