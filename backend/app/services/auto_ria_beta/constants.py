"""Публічний HTML-пошук auto.ria.com (без платного REST API)."""

AUTO_RIA_BETA_SOURCE = "auto_ria_beta"
AUTO_RIA_BETA_LABEL = "AUTO.RIA test beta"

BASE_URL = "https://auto.ria.com"
SEARCH_URL = f"{BASE_URL}/uk/search/"
MARKS_API = "http://api.auto.ria.com/categories/{category_id}/marks"

CATEGORY_LEGKOVI = 1
PAGE_SIZE = 100
MAX_PAGES = 25
POOL_MAX_ITEMS = 2500
# Live-пошук: одна HTML-сторінка зараз, наступні — коли користувач гортає.
INITIAL_HTML_PAGES = 1
REQUEST_DELAY_SECONDS = 0.35

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
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Referer": BASE_URL,
}
