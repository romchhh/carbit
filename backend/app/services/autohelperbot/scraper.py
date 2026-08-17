"""Парсинг аукціонної історії VIN через autohelperbot.com (Playwright).

Вузькі місця старого шляху (десятки секунд «тиші»):
- wait_until=networkidle на картці авто (аналітика/сокети майже ніколи не затихають);
- wait_for_timeout() після кожного кроку (~8 с мертвого очікування);
- type(..., delay=80) замість fill();
- окремий CDP-раунд на кожне посилання/фото.

Новий шлях: domcontentloaded + очікування конкретного селектора, fill(),
один page.evaluate() для даних, блокування картинок/шрифтів/трекерів.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

from app.services.autohelperbot.errors import AutohelperbotError, AutohelperbotNotFound

logger = logging.getLogger(__name__)

BASE_URL = "https://autohelperbot.com"
SEARCH_URL = f"{BASE_URL}/car-search"
CAR_URL_RE = re.compile(r"/car/[A-Z0-9]{17}", re.IGNORECASE)
CAR_VIN_RE = re.compile(r"/car/([A-Z0-9]{17})", re.IGNORECASE)
CAR_LOT_RE = re.compile(r"/car/[A-Z0-9]{17}_(\d+)", re.IGNORECASE)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['uk-UA', 'uk', 'ru', 'en-US', 'en'] });
Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (p) =>
    p.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : origQuery(p);
"""

PATTERNS = {
    "mileage": r"Пробег\s+([\d\s,]+(?:km|mi))",
    "mileage_km": r"Пробег\s+[\d\s,]+(?:km|mi)\s+([\d\s,]+km)",
    "sale_date": r"Дата продажи \(UTC\)\s+(\d{2}\.\d{2}\.\d{4}[^\n]*)",
    "sale_price": r"Цена продажи:\s*\$\s*([\d\s]+(?:CAD|USD)?)",
    "sale_records": r"Записей о продаже:\s*(\d+)",
    "engine": r"Двигатель\s+([^\n]+)",
    "color": r"Цвет\s+([^\n]+)",
    "transmission": r"Коробка передач\s+([^\n]+)",
    "fuel": r"Топливо\s+([^\n]+)",
    "drive": r"Привод\s+([^\n]+)",
    "keys": r"Ключи\s+([^\n]+)",
    "repair_cost": r"Стоимость ремонта\s+\$\s*([\d\s]+(?:CAD|USD)?)",
    "market_value": r"Рыночная стоимость\s+\$\s*([\d\s]+(?:CAD|USD)?)",
    "primary_damage": r"Основное повреждение\s+([^\n]+)",
    "primary_damage_en": r"Основное повреждение:\s*([A-Z][A-Z0-9 \-/]+)",
    "exterior_condition": r"Внешнее состояние\s+([^\n]+)",
    "avg_price": r"Средняя цена:\s+\$\s*([\d\s]+(?:CAD|USD)?)",
}

REPORT_LINK_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("carhistory", re.compile(r"check_vin\?vin=", re.I)),
    ("autocheck", re.compile(r"check-autocheck\?vin=", re.I)),
    ("window_sticker", re.compile(r"check-windowsticker\?vin=", re.I)),
    ("copart", re.compile(r"copart\.com/lot/", re.I)),
    ("iaai", re.compile(r"iaai\.com/", re.I)),
]

# Один локатор замість послідовних wait_for по 2 с на селектор.
INPUT_SELECTOR = ", ".join(
    [
        "input[placeholder*='VIN' i]",
        "input[placeholder*='Lot' i]",
        "input[placeholder*='vin' i]",
        "input[name*='vin' i]",
        "input[name*='search' i]",
        "input[type='search']",
        "form input[type='text']",
        "input[type='text']",
    ]
)

# Картинки не блокуємо — IAAI-галерея з’являється як <img src="s2.autohelperbot.com/{VIN}-*.jpg">.
BLOCKED_RESOURCE_TYPES = frozenset({"media", "font"})
BLOCKED_URL_SNIPPETS = (
    "google-analytics.com",
    "googletagmanager.com",
    "googleadservices.com",
    "doubleclick.net",
    "facebook.net",
    "facebook.com/tr",
    "mc.yandex.ru",
    "hotjar.com",
    "clarity.ms",
)

_DUMP_PAGE_JS = """() => {
    const abs = (h) => {
        try { return new URL(h, location.origin).href; } catch { return h || ''; }
    };
    const images = [];
    const push = (url, alt) => {
        const full = abs(url);
        if (full) images.push({ url: full, alt: alt || '' });
    };
    for (const img of document.querySelectorAll('img')) {
        const alt = img.getAttribute('alt') || '';
        push(img.getAttribute('src') || img.src, alt);
        push(img.getAttribute('data-src') || img.getAttribute('data-lazy') || img.getAttribute('data-original'), alt);
        const srcset = img.getAttribute('srcset') || '';
        for (const part of srcset.split(',')) {
            const u = part.trim().split(/\\s+/)[0];
            if (u) push(u, alt);
        }
    }
    const html = document.documentElement ? document.documentElement.innerHTML : '';
    const re = /https?:\\/\\/s2\\.autohelperbot\\.com\\/[^"'\\\\s>]+\\.(?:jpe?g|webp|png)/gi;
    for (const m of html.matchAll(re)) push(m[0], '');
    return {
        url: location.href,
        title: (document.querySelector('h1')?.innerText || '').trim(),
        body: document.body ? document.body.innerText : '',
        meta_description: document.querySelector('meta[name="description"]')?.content || '',
        og_image: document.querySelector('meta[property="og:image"]')?.content || '',
        hrefs: [...document.querySelectorAll('a[href]')].map(a => abs(a.getAttribute('href') || '')).filter(Boolean),
        images,
    };
}"""

_FIND_CAR_URL_JS = """(vin) => {
    const upper = (vin || '').toUpperCase();
    if (/\\/car\\/[A-Z0-9]{17}/i.test(location.href)) return location.href;
    const hrefs = [...document.querySelectorAll('a[href]')].map(a => a.href);
    const car = hrefs.filter(h => /\\/car\\/[A-Z0-9]/i.test(h));
    const exact = car.find(h => h.toUpperCase().includes(upper));
    return exact || car[0] || null;
}"""

_pw = None
_browser = None
_browser_lock = asyncio.Lock()
_browser_headed: bool | None = None


def abs_autohelper_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(BASE_URL + "/", href)


def pick_car_url(current_url: str, hrefs: list[str], vin: str) -> str | None:
    if CAR_URL_RE.search(current_url or ""):
        return current_url
    vin_u = vin.upper()
    car_links: list[str] = []
    for href in hrefs:
        full = abs_autohelper_url(href)
        if CAR_URL_RE.search(full) or re.search(r"/car/[A-Z0-9]", full, re.IGNORECASE):
            car_links.append(full)
    if not car_links:
        return None
    for link in car_links:
        if vin_u in link.upper():
            return link
    return car_links[0]


def parse_specs(body: str, meta: str = "") -> dict[str, str]:
    specs: dict[str, str] = {}
    for key, pat in PATTERNS.items():
        m2 = re.search(pat, body, re.IGNORECASE)
        if m2:
            specs[key] = m2.group(1).strip()

    if specs.get("primary_damage"):
        damage = specs["primary_damage"].strip()
        if damage.startswith(":"):
            damage = damage.lstrip(": ").strip()
        if re.fullmatch(r"[A-Z][A-Z0-9 \-/]+", damage):
            specs.setdefault("primary_damage_en", damage)
            m_ua = re.search(r"Основное повреждение\s*\n\s*([^\n:]+)", body)
            if m_ua and not re.fullmatch(r"[A-Z][A-Z0-9 \-/]+", m_ua.group(1).strip()):
                specs["primary_damage"] = m_ua.group(1).strip()
            else:
                specs["primary_damage"] = damage
        else:
            specs["primary_damage"] = damage.split("\n")[0].strip()

    if meta and not specs.get("primary_damage"):
        m2 = re.search(r"повреждение:\s*([^|]+)", meta, re.IGNORECASE)
        if m2:
            specs["primary_damage"] = m2.group(1).strip()
    return specs


def pick_report_links(hrefs: list[str]) -> dict[str, str]:
    links: dict[str, str] = {}
    for href in hrefs:
        full = abs_autohelper_url(href)
        if not full.startswith("http"):
            continue
        for key, pattern in REPORT_LINK_RULES:
            if key in links:
                continue
            if pattern.search(full):
                links[key] = full
    return links


def _clean_title(raw: str | None, vin: str | None) -> str | None:
    if not raw:
        return None
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return None
    title = lines[0]
    if vin and title.upper() == vin.upper() and len(lines) > 1:
        title = lines[1]
    if vin:
        title = re.sub(re.escape(vin), "", title, flags=re.IGNORECASE).strip(" \n\t|-")
    return title or lines[0]


def _photo_caption(alt: str, vin: str | None) -> str:
    caption = (alt or "").strip()
    if vin:
        caption = re.sub(re.escape(vin), "", caption, flags=re.IGNORECASE).strip()
    caption = re.sub(r"\bvin:\s*$", "", caption, flags=re.IGNORECASE).strip()
    caption = re.sub(r"\s{2,}", " ", caption)
    return caption


_SKIP_PHOTO_SNIPPETS = (
    "/img/langs/",
    "/img/chatgpt",
    "/img/gemini",
    "favicon",
    "graph-blured",
    "test_logo",
)


def _is_auction_photo_url(src: str) -> bool:
    lower = src.lower()
    if any(snip in lower for snip in _SKIP_PHOTO_SNIPPETS):
        return False
    if "s2.autohelperbot.com" in lower:
        return True
    if "-590" in lower:
        return True
    if "copart.com" in lower or "iaai.com" in lower:
        return True
    if re.search(r"\.(jpe?g|webp)(\?|$)", lower):
        host = lower.split("/")[2] if "://" in lower else ""
        if "autohelperbot.com" in host and "/img/" not in lower:
            return True
    return False


def pick_photos(images: list[dict[str, str]], vin: str | None) -> list[dict[str, str]]:
    photos: list[dict[str, str]] = []
    seen: set[str] = set()
    vin_u = (vin or "").upper()
    for item in images:
        src = abs_autohelper_url(item.get("url") or "")
        alt = item.get("alt") or ""
        if not src or src in seen:
            continue
        if not _is_auction_photo_url(src):
            continue
        blob = f"{src} {alt}".upper()
        if vin_u and vin_u not in blob:
            continue
        seen.add(src)
        photos.append({"url": src, "caption": _photo_caption(alt, vin)})
    return photos


def build_result_from_dump(dump: dict[str, Any]) -> dict[str, Any]:
    page_url = dump.get("url") if isinstance(dump.get("url"), str) else ""
    result: dict[str, Any] = {"page_url": page_url}

    m = CAR_VIN_RE.search(page_url)
    vin = m.group(1).upper() if m else None
    if vin:
        result["vin"] = vin

    lot_m = CAR_LOT_RE.search(page_url)
    if lot_m:
        result["lot_id"] = lot_m.group(1)

    title = dump.get("title") if isinstance(dump.get("title"), str) else None
    result["title"] = _clean_title(title, vin)

    meta = dump.get("meta_description") if isinstance(dump.get("meta_description"), str) else ""
    og_image = dump.get("og_image") if isinstance(dump.get("og_image"), str) else None
    if meta:
        result["meta_description"] = meta
    if og_image:
        result["og_image"] = og_image

    body = dump.get("body") if isinstance(dump.get("body"), str) else ""
    specs = parse_specs(body, meta)
    result["specs"] = specs

    hrefs = dump.get("hrefs") if isinstance(dump.get("hrefs"), list) else []
    links = pick_report_links([h for h in hrefs if isinstance(h, str)])
    if links.get("copart"):
        result["copart_url"] = links["copart"]
    if links.get("iaai"):
        result["iaai_url"] = links["iaai"]
    result["links"] = links

    images_raw = dump.get("images") if isinstance(dump.get("images"), list) else []
    images: list[dict[str, str]] = []
    if og_image:
        images.append({"url": og_image, "alt": title or ""})
    for item in images_raw:
        if isinstance(item, dict):
            images.append(
                {
                    "url": item.get("url") if isinstance(item.get("url"), str) else "",
                    "alt": item.get("alt") if isinstance(item.get("alt"), str) else "",
                }
            )
    photos = pick_photos(images, vin)
    result["photos"] = photos
    result["photos_count"] = len(photos)
    return result


async def _close_browser_unlocked() -> None:
    global _pw, _browser, _browser_headed
    browser, pw = _browser, _pw
    _browser = None
    _pw = None
    _browser_headed = None
    if browser is not None:
        try:
            await browser.close()
        except Exception:
            logger.debug("VIN browser close failed", exc_info=True)
    if pw is not None:
        try:
            await pw.stop()
        except Exception:
            logger.debug("VIN playwright stop failed", exc_info=True)


async def close_shared_browser() -> None:
    async with _browser_lock:
        await _close_browser_unlocked()


async def _get_shared_browser(*, headed: bool):
    """Один Chromium на процес — запуск браузера займає 1–3 с на кожен VIN."""
    global _pw, _browser, _browser_headed
    async with _browser_lock:
        if _browser is not None:
            if _browser_headed == headed:
                try:
                    if _browser.is_connected():
                        return _browser
                except Exception:
                    pass
            await _close_browser_unlocked()

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise AutohelperbotError(
                "Playwright не встановлено для перевірки аукціонної історії",
                status_code=503,
            ) from exc

        try:
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(
                headless=not headed,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--no-first-run",
                    "--disable-infobars",
                ],
            )
        except Exception as exc:
            msg = str(exc)
            if "Executable doesn't exist" in msg or "playwright install" in msg.lower():
                raise AutohelperbotError(
                    "Браузер Playwright не встановлено. У корені проєкту виконай: "
                    ".venv/bin/playwright install chromium",
                    status_code=503,
                ) from exc
            raise AutohelperbotError(
                f"Не вдалося запустити браузер для аукціонної історії: {exc}",
                status_code=503,
            ) from exc

        _pw = pw
        _browser = browser
        _browser_headed = headed
        return browser


async def _install_speed_routes(page) -> None:
    async def handler(route) -> None:
        request = route.request
        url = request.url
        if request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
        if any(snippet in url for snippet in BLOCKED_URL_SNIPPETS):
            await route.abort()
            return
        await route.continue_()

    await page.route("**/*", handler)


async def _pass_cloudflare(page, vin: str) -> None:
    title = await page.title()
    lowered = title.lower()
    if "just a moment" not in lowered and "cloudflare" not in lowered:
        return
    logger.warning("autohelperbot CF challenge for VIN=%s", vin)
    try:
        await page.wait_for_function(
            """() => {
                const t = (document.title || '').toLowerCase();
                return !t.includes('just a moment') && !t.includes('cloudflare');
            }""",
            timeout=20_000,
        )
    except Exception as exc:
        raise AutohelperbotError(
            "Не вдалося пройти Cloudflare на autohelperbot",
            status_code=503,
        ) from exc


async def _wait_for_car_or_empty(page, timeout: int = 12_000) -> None:
    try:
        await page.wait_for_function(
            """() => {
                if (window.location.pathname.includes('/car/')) return true;
                const links = document.querySelectorAll('a[href*="/car/"]');
                if (links.length) return true;
                const body = (document.body && document.body.innerText) || '';
                if (body.includes('не найден') || body.includes('not found')) return true;
                return false;
            }""",
            timeout=timeout,
        )
    except Exception:
        pass


async def _find_car_url(page, vin: str) -> str | None:
    await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=20_000)
    await _pass_cloudflare(page, vin)

    locator = page.locator(INPUT_SELECTOR).first
    try:
        await locator.wait_for(state="visible", timeout=8_000)
    except Exception as exc:
        raise AutohelperbotError("Поле пошуку VIN не знайдено на autohelperbot") from exc

    await locator.click()
    await locator.fill(vin)

    submit_btn = page.locator(
        "button[type='submit'], button.search, form button, input[type='submit']"
    ).first
    try:
        await submit_btn.click(timeout=1_500)
    except Exception:
        await locator.press("Enter")

    await _wait_for_car_or_empty(page, timeout=12_000)

    try:
        found = await page.evaluate(_FIND_CAR_URL_JS, vin)
    except Exception:
        found = None
    if isinstance(found, str) and found:
        return found

    current_url = page.url
    hrefs: list[str] = []
    try:
        hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(a => a.href)")
    except Exception:
        hrefs = []
    return pick_car_url(current_url, hrefs, vin)


async def _extract_data(page) -> dict[str, Any]:
    dump = await page.evaluate(_DUMP_PAGE_JS)
    if not isinstance(dump, dict):
        dump = {"url": page.url}
    return build_result_from_dump(dump)


async def scrape_vin_auction(vin: str, *, headed: bool = False) -> dict[str, Any]:
    """Повертає сирий dict з картки autohelperbot або кидає помилку."""
    vin = vin.strip().upper()
    started = time.monotonic()
    browser = await _get_shared_browser(headed=headed)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="ru-RU",
        timezone_id="Europe/Kiev",
    )
    await context.add_init_script(STEALTH_JS)
    page = await context.new_page()
    try:
        await _install_speed_routes(page)
        t1 = time.monotonic()
        car_url = await _find_car_url(page, vin)
        logger.info(
            "VIN auction search done vin=%s url=%s dt=%.1fs",
            vin,
            car_url,
            time.monotonic() - t1,
        )
        if not car_url:
            raise AutohelperbotNotFound(vin)

        t2 = time.monotonic()
        await page.goto(car_url, wait_until="domcontentloaded", timeout=20_000)
        try:
            await page.wait_for_function(
                """() => {
                    const h1 = (document.querySelector('h1')?.innerText || '').trim();
                    const body = (document.body && document.body.innerText) || '';
                    return h1.length > 0 || body.length > 180;
                }""",
                timeout=8_000,
            )
        except Exception:
            pass
        try:
            await page.wait_for_selector(
                'img[src*="s2.autohelperbot"], img[src*="-590"]',
                timeout=5_000,
            )
        except Exception:
            pass
        data = await _extract_data(page)
        logger.info(
            "VIN auction card parsed vin=%s specs=%s photos=%s dt=%.1fs total=%.1fs",
            vin,
            bool(data.get("specs")),
            data.get("photos_count"),
            time.monotonic() - t2,
            time.monotonic() - started,
        )
        if not data.get("specs") and not data.get("title"):
            raise AutohelperbotNotFound(vin)
        return data
    finally:
        await context.close()
        # headed — одноразовий браузер для дебагу, не лишаємо в пулі
        if headed:
            await close_shared_browser()
