"""Бейджі з публічної сторінки AUTO.RIA (developers API їх не віддає)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.services.auto_ria.constants import AUTO_RIA_SITE_URL

logger = logging.getLogger(__name__)

_USA_ORIGIN_RE = re.compile(r"сша|usa|америк|штати|copart|iaai", re.IGNORECASE)

_BADGE_VISIBLE_RE = re.compile(
    r'"id"\s*:\s*"(?P<id>badgesOrderFrom|badgesDamaged)"\s*,\s*"isHide"\s*:\s*false',
    re.IGNORECASE,
)
_BADGE_CONTENT_RE = re.compile(
    r'"id"\s*:\s*"(?P<id>badgesOrderFrom|badgesDamaged)"\s*,\s*"isHide"\s*:\s*false'
    r'.{0,1200}?"content"\s*:\s*"(?P<content>(?:\\.|[^"\\])*)"',
    re.IGNORECASE | re.DOTALL,
)

_SITE_CLIENT: httpx.AsyncClient | None = None


async def _site_client() -> httpx.AsyncClient:
    global _SITE_CLIENT
    if _SITE_CLIENT is None or _SITE_CLIENT.is_closed:
        _SITE_CLIENT = httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Carbit/1.0)"},
        )
    return _SITE_CLIENT


def _unescape_badge_content(value: str) -> str:
    try:
        parsed = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        parsed = value
    return parsed if isinstance(parsed, str) else str(parsed)


def parse_page_badges_html(html: str) -> dict[str, bool]:
    """Парсить видимі бейджі з SSR-розмітки сторінки оголошення."""
    visible: set[str] = set()
    contents: dict[str, str] = {}
    for match in _BADGE_VISIBLE_RE.finditer(html or ""):
        visible.add(match.group("id").lower())
    for match in _BADGE_CONTENT_RE.finditer(html or ""):
        contents[match.group("id").lower()] = _unescape_badge_content(match.group("content"))

    if not visible:
        return {}

    out: dict[str, bool] = {}
    if "badgesorderfrom" in visible:
        origin = contents.get("badgesorderfrom") or ""
        out["usa_import"] = bool(_USA_ORIGIN_RE.search(origin))
    if "badgesdamaged" in visible:
        out["had_accident"] = True
    return out


async def fetch_page_badges(listing_url: str) -> dict[str, bool]:
    """Завантажує публічну сторінку та витягує бейджі USA / ДТП."""
    url = (listing_url or "").strip()
    if not url.startswith("http"):
        return {}

    try:
        client = await _site_client()
        response = await client.get(url)
        response.raise_for_status()
    except Exception:
        logger.debug("AUTO.RIA page badges fetch failed for %s", url, exc_info=True)
        return {}

    return parse_page_badges_html(response.text)


async def attach_page_badges_to_info(info: dict[str, Any]) -> dict[str, Any]:
    """Додає `ria_page_badges` до відповіді /auto/info (USA не приходить у developers API)."""
    link = str(info.get("linkToView") or "").strip()
    if not link:
        return info

    listing_url = link if link.startswith("http") else f"{AUTO_RIA_SITE_URL}{link}"
    badges = await fetch_page_badges(listing_url)
    if not badges:
        return info

    enriched = dict(info)
    enriched["ria_page_badges"] = badges
    return enriched
