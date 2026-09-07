UDRIVE_API_BASE_URL = "https://api.udrive.store/api/v1"
UDRIVE_SITE_URL = "https://udrive.com.ua"


def udrive_listing_url(car_id: str) -> str:
    """Публічна сторінка авто: /catalog/cars/{uuid} (без slug марки)."""
    normalized = str(car_id or "").strip().lower()
    if not normalized:
        return UDRIVE_SITE_URL
    return f"{UDRIVE_SITE_URL}/catalog/cars/{normalized}"
UDRIVE_CDN_BASE = "https://ik.imagekit.io/udriveapp/production/"
UDRIVE_CDN_TRANSFORM = "?tr=q-80"

UDRIVE_PAGE_SIZE = 50
STATUS_PUBLISHED = 1

FUEL_MAP = {
    "petrol": "Бензин",
    "diesel": "Дизель",
    "hybrid": "Гібрид",
    "electric": "Електро",
    "gas": "Газ",
}

GEARBOX_MAP = {
    "at": "Автомат",
    "mt": "Механіка",
    "am": "Робот",
    "cvt": "Варіатор",
}
