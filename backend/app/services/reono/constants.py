from __future__ import annotations

REONO_BASE_URL = "https://reono.ua"
REONO_CATALOG_PATH = "legkovoe-avto"

REONO_PAGE_SIZE = 40
REONO_MAX_PAGES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Referer": REONO_BASE_URL,
}

REGION_SLUGS: dict[str, str] = {
    "kharkiv": "xarkovskaya-oblast",
    "kharkivska": "xarkovskaya-oblast",
    "харківська": "xarkovskaya-oblast",
    "kyiv": "kievskaya-oblast",
    "kyivska": "kievskaya-oblast",
    "київська": "kievskaya-oblast",
    "kievskaya": "kievskaya-oblast",
    "chernivtsi": "chernovickaya-oblast",
    "chernivetska": "chernovickaya-oblast",
    "чернівецька": "chernovickaya-oblast",
    "poltava": "poltavskaya-oblast",
    "poltavska": "poltavskaya-oblast",
    "полтавська": "poltavskaya-oblast",
    "ternopil": "ternopolskaya-oblast",
    "ternopilska": "ternopolskaya-oblast",
    "тернопільська": "ternopolskaya-oblast",
    "dnipro": "dnepropetrovskaya-oblast",
    "dnipropetrovska": "dnepropetrovskaya-oblast",
    "дніпропетровська": "dnepropetrovskaya-oblast",
    "kherson": "xersonskaya-oblast",
    "khersonska": "xersonskaya-oblast",
    "херсонська": "xersonskaya-oblast",
    "ivano-frankivsk": "ivano-frankovskaya-oblast",
    "івано-франківська": "ivano-frankovskaya-oblast",
    "crimea": "krym-avtonomnaya-respublika",
    "lviv": "lvovskaya-oblast",
    "lvivska": "lvovskaya-oblast",
    "львівська": "lvovskaya-oblast",
    "odesa": "odesskaya-oblast",
    "odeska": "odesskaya-oblast",
    "одеськ": "odesskaya-oblast",
    "одеська": "odesskaya-oblast",
    "vinnytsia": "vinnickaya-oblast",
    "vinnitska": "vinnickaya-oblast",
    "вінницька": "vinnickaya-oblast",
    "zhytomyr": "zhitomirskaya-oblast",
    "zhytomyrska": "zhitomirskaya-oblast",
    "житомирська": "zhitomirskaya-oblast",
    "zaporizhzhia": "zaporozhskaya-oblast",
    "zaporizka": "zaporozhskaya-oblast",
    "запорізька": "zaporozhskaya-oblast",
    "sumy": "sumskaya-oblast",
    "sumska": "sumskaya-oblast",
    "сумська": "sumskaya-oblast",
    "cherkasy": "cherkasskaya-oblast",
    "cherkaska": "cherkasskaya-oblast",
    "черкаська": "cherkasskaya-oblast",
    "chernihiv": "chernigovskaya-oblast",
    "chernihivska": "chernigovskaya-oblast",
    "чернігівська": "chernigovskaya-oblast",
    "rivne": "rovenskaya-oblast",
    "rivnenska": "rovenskaya-oblast",
    "рівненська": "rovenskaya-oblast",
    "volyn": "volynskaya-oblast",
    "volynska": "volynskaya-oblast",
    "волинська": "volynskaya-oblast",
    "zakarpattia": "zakarpatskaya-oblast",
    "zakarpatska": "zakarpatskaya-oblast",
    "закарпатська": "zakarpatskaya-oblast",
    "mykolaiv": "nikolaevskaya-oblast",
    "mykolaivska": "nikolaevskaya-oblast",
    "миколаївська": "nikolaevskaya-oblast",
}

GEARBOX_LABELS: dict[str, str] = {
    "variator": "Варіатор",
    "automatic": "Автомат",
    "auto": "Автомат",
    "manual": "Механіка",
    "robot": "Робот",
    "tiptronic": "Типтронік",
}

FUEL_LABELS: dict[str, str] = {
    "petrol": "Бензин",
    "diesel": "Дизель",
    "gas": "Газ",
    "hybrid": "Гібрид",
    "electric": "Електро",
    "methane": "Метан",
}
