IMPERIYA_API_BASE_URL = "https://api.imperiya-auto.com.ua"
IMPERIYA_SITE_URL = "https://imperiya-auto.com.ua"

IMPERIYA_MAX_LIMIT = 50

# Carbit sort → Imperiya sortBy
SORT_TO_IMPERIYA: dict[str, str] = {
    "newest": "date",
    "published_desc": "date",
    "oldest": "year_old",
    "price_asc": "price_asc",
    "price_desc": "price_desc",
    "year_desc": "year_new",
    "year_asc": "year_old",
    "mileage_asc": "mileage",
}
