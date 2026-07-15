from __future__ import annotations

BASE_URL = "https://www.olx.ua"
CATEGORY_PATH = "/uk/transport/legkovye-avtomobili"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

REQUEST_TIMEOUT = 15.0
MIN_DELAY = 0.4
MAX_DELAY = 1.2
MAX_RETRIES = 3

FUEL_MAP = {
    "petrol": "1",
    "diesel": "2",
    "gas": "5",
    "electric": "6",
    "hybrid": "7",
}

CONDITION_MAP = {
    "used": "2",
    "new": "1",
}

TRANSMISSION_MAP = {
    "manual": "1",
    "automatic": "2",
    "robot": "3",
    "variator": "4",
}

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

REGION_TO_CITY_QUERY: dict[str, str] = {
    "м. київ": "kyiv",
    "київська область": "київська-область",
    "вінницька область": "вінницька-область",
    "волинська область": "волинська-область",
    "дніпропетровська область": "дніпропетровська-область",
    "донецька область": "донецька-область",
    "житомирська область": "житомирська-область",
    "закарпатська область": "закарпатська-область",
    "запорізька область": "запорізька-область",
    "івано-франківська область": "івано-франківська-область",
    "кіровоградська область": "кіровоградська-область",
    "луганська область": "луганська-область",
    "львівська область": "львівська-область",
    "миколаївська область": "миколаївська-область",
    "одеська область": "одеська-область",
    "полтавська область": "полтавська-область",
    "рівненська область": "рівненська-область",
    "сумська область": "сумська-область",
    "тернопільська область": "тернопільська-область",
    "харківська область": "харківська-область",
    "херсонська область": "херсонська-область",
    "хмельницька область": "хмельницька-область",
    "черкаська область": "черкаська-область",
    "чернівецька область": "чернівецька-область",
    "чернігівська область": "чернігівська-область",
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
