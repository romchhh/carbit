from __future__ import annotations

CAR_MARKET_BASE_URL = "https://car-market.net"
CAR_MARKET_CATALOG_URL = f"{CAR_MARKET_BASE_URL}/catalog"

CAR_MARKET_PAGE_SIZE = 20
# HTML-сканування — не більше 3 сторінок у live-пулі (швидкість).
CAR_MARKET_MAX_PAGES = 3

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
    "Referer": CAR_MARKET_BASE_URL,
}

FUEL_CODES: dict[str, str] = {
    "petrol": "1",
    "бензин": "1",
    "diesel": "2",
    "дизель": "2",
    "gas": "3",
    "газ": "3",
    "газ пропан+бензин": "3",
    "газ пропан-бутан+бензин": "3",
    "electric": "4",
    "електро": "4",
    "hybrid": "5",
    "гібрид": "5",
    "methane": "6",
    "метан": "6",
    "газ метан+бензин": "6",
}

TRANSMISSION_CODES: dict[str, str] = {
    "auto": "1",
    "автомат": "1",
    "manual": "2",
    "механіка": "2",
    "ручна": "2",
    "variator": "3",
    "варіатор": "3",
    "robot": "4",
    "робот": "4",
    "tiptronic": "5",
    "типтронік": "5",
}

DRIVE_CODES: dict[str, str] = {
    "front": "1",
    "передній": "1",
    "awd": "2",
    "повний": "2",
    "rear": "3",
    "задній": "3",
}

BODY_CODES: dict[str, str] = {
    "suv": "1",
    "позашляховик": "1",
    "кросовер": "1",
    "hatchback": "2",
    "хетчбек": "2",
    "sedan": "3",
    "седан": "3",
    "coupe": "4",
    "купе": "4",
    "liftback": "5",
    "ліфтбек": "5",
    "universal": "6",
    "універсал": "6",
    "minivan": "7",
    "мінівен": "7",
}

BRAND_IDS: dict[str, str] = {
    "audi": "6628",
    "volkswagen": "6560",
    "toyota": "6450",
    "bmw": "6420",
    "ford": "6480",
    "hyundai": "6490",
    "honda": "6570",
    "nissan": "6540",
    "mercedes": "6510",
    "mercedes-benz": "6510",
    "kia": "6485",
    "mazda": "6520",
    "renault": "6545",
    "skoda": "6555",
    "peugeot": "6535",
    "opel": "6530",
    "volvo": "6580",
    "porsche": "6538",
    "mitsubishi": "6525",
    "chevrolet": "6440",
    "subaru": "6555",
    "lexus": "6500",
    "jeep": "6495",
    "land rover": "6498",
    "suzuki": "6558",
}
