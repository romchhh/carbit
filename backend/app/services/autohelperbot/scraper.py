"""Парсинг аукціонної історії VIN через autohelperbot.com (Playwright).

Порт логіки з кореневого vintest.py.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.autohelperbot.errors import AutohelperbotError, AutohelperbotNotFound

logger = logging.getLogger(__name__)

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

INPUT_SELECTORS = [
    "input[placeholder*='VIN']",
    "input[placeholder*='Lot']",
    "input[placeholder*='vin']",
    "input[name*='vin']",
    "input[name*='search']",
    "input[type='search']",
    "input[type='text']",
    "input",
]


async def _wait_for_navigation_or_results(page, timeout: int = 15000) -> None:
    try:
        await page.wait_for_function(
            """() => {
                if (window.location.pathname.includes('/car/')) return true;
                const links = [...document.querySelectorAll('a[href]')];
                if (links.some(a => a.href.includes('/car/'))) return true;
                const body = document.body.innerText;
                if (body.includes('не найден') || body.includes('not found')) return true;
                return false;
            }""",
            timeout=timeout,
        )
    except Exception:
        pass


async def _find_car_url(page, vin: str) -> str | None:
    await page.goto(
        "https://autohelperbot.com/car-search",
        wait_until="domcontentloaded",
        timeout=40000,
    )
    await page.wait_for_timeout(2000)

    title = await page.title()
    if "Just a moment" in title or "Cloudflare" in title:
        logger.warning("autohelperbot CF challenge for VIN=%s", vin)
        try:
            await page.wait_for_url(
                re.compile(r"autohelperbot\.com(?!/cdn-cgi)"),
                timeout=90000,
            )
            await page.wait_for_timeout(2000)
        except Exception as exc:
            raise AutohelperbotError(
                "Не вдалося пройти Cloudflare на autohelperbot",
                status_code=503,
            ) from exc

    locator = None
    for sel in INPUT_SELECTORS:
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="visible", timeout=2000)
            locator = loc
            break
        except Exception:
            continue

    if not locator:
        raise AutohelperbotError("Поле пошуку VIN не знайдено на autohelperbot")

    await locator.click()
    await page.wait_for_timeout(200)
    await locator.click(click_count=3)
    await page.wait_for_timeout(200)
    await locator.type(vin, delay=80)
    await page.wait_for_timeout(800)

    submit_btn = page.locator(
        "button[type='submit'], button.search, form button, input[type='submit']"
    ).first
    try:
        await submit_btn.wait_for(state="visible", timeout=2000)
        await submit_btn.click()
    except Exception:
        await locator.press("Enter")

    await _wait_for_navigation_or_results(page, timeout=15000)
    await page.wait_for_timeout(1500)

    current_url = page.url
    if re.search(r"/car/[A-Z0-9]{17}", current_url, re.IGNORECASE):
        return current_url

    links = await page.query_selector_all("a[href]")
    car_links: list[str] = []
    for link in links:
        href = await link.get_attribute("href") or ""
        if re.search(r"/car/[A-Z0-9]", href, re.IGNORECASE):
            full = href if href.startswith("http") else f"https://autohelperbot.com{href}"
            car_links.append(full)

    if not car_links:
        return None

    for link in car_links:
        if vin.upper() in link.upper():
            return link
    return car_links[0]


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
    caption = re.sub(r"\s{2,}", " ", caption)
    return caption


async def _extract_data(page) -> dict[str, Any]:
    result: dict[str, Any] = {"page_url": page.url}

    m = re.search(r"/car/([A-Z0-9]{17})", page.url, re.IGNORECASE)
    vin = m.group(1).upper() if m else None
    if vin:
        result["vin"] = vin

    lot_m = re.search(r"/car/[A-Z0-9]{17}_(\d+)", page.url, re.IGNORECASE)
    if lot_m:
        result["lot_id"] = lot_m.group(1)

    h1 = await page.query_selector("h1")
    if h1:
        result["title"] = _clean_title((await h1.inner_text()).strip(), vin)

    for attr, sel in [
        ("meta_description", 'meta[name="description"]'),
        ("og_image", 'meta[property="og:image"]'),
    ]:
        el = await page.query_selector(sel)
        if el:
            val = await el.get_attribute("content")
            if val:
                result[attr] = val

    body = await page.inner_text("body")
    specs: dict[str, str] = {}
    for key, pat in PATTERNS.items():
        m2 = re.search(pat, body, re.IGNORECASE)
        if m2:
            specs[key] = m2.group(1).strip()

    if specs.get("primary_damage"):
        damage = specs["primary_damage"].strip()
        if damage.startswith(":"):
            damage = damage.lstrip(": ").strip()
        # Prefer UA/RU wording; keep EN separately
        if re.fullmatch(r"[A-Z][A-Z0-9 \-/]+", damage):
            specs.setdefault("primary_damage_en", damage)
            m_ua = re.search(
                r"Основное повреждение\s*\n\s*([^\n:]+)",
                body,
            )
            if m_ua and not re.fullmatch(r"[A-Z][A-Z0-9 \-/]+", m_ua.group(1).strip()):
                specs["primary_damage"] = m_ua.group(1).strip()
            else:
                specs["primary_damage"] = damage
        else:
            specs["primary_damage"] = damage.split("\n")[0].strip()

    meta = result.get("meta_description", "")
    if meta and not specs.get("primary_damage"):
        m2 = re.search(r"повреждение:\s*([^|]+)", meta, re.IGNORECASE)
        if m2:
            specs["primary_damage"] = m2.group(1).strip()

    result["specs"] = specs

    links: dict[str, str] = {}
    for a in await page.query_selector_all("a[href]"):
        href = await a.get_attribute("href") or ""
        if href.startswith("/"):
            href = f"https://autohelperbot.com{href}"
        if not href.startswith("http"):
            continue
        for key, pattern in REPORT_LINK_RULES:
            if key in links:
                continue
            if pattern.search(href):
                links[key] = href
    if links.get("copart"):
        result["copart_url"] = links["copart"]
    if links.get("iaai"):
        result["iaai_url"] = links["iaai"]
    result["links"] = links

    photos: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for img in await page.query_selector_all('img[src*="-590"]'):
        src = await img.get_attribute("src") or ""
        alt = await img.get_attribute("alt") or ""
        if not src or src in seen_urls:
            continue
        if vin:
            blob = f"{src} {alt}".upper()
            if vin not in blob:
                continue
        seen_urls.add(src)
        photos.append({"url": src, "caption": _photo_caption(alt, vin)})
    result["photos"] = photos
    result["photos_count"] = len(photos)
    return result


async def scrape_vin_auction(vin: str, *, headed: bool = False) -> dict[str, Any]:
    """Повертає сирий dict з картки autohelperbot або кидає помилку."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise AutohelperbotError(
            "Playwright не встановлено для перевірки аукціонної історії",
            status_code=503,
        ) from exc

    vin = vin.strip().upper()
    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(
                headless=not headed,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
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
        try:
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
            car_url = await _find_car_url(page, vin)
            if not car_url:
                raise AutohelperbotNotFound(vin)

            await page.goto(car_url, wait_until="networkidle", timeout=40000)
            await page.wait_for_timeout(2000)
            data = await _extract_data(page)
            if not data.get("specs") and not data.get("title"):
                raise AutohelperbotNotFound(vin)
            return data
        finally:
            await browser.close()
