"""Проксі для HTML-пошуку OLX / AUTO.RIA (Webshare). Мінімум трафіку."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_WEBSHARE_CONFIG_URL = "https://proxy.webshare.io/api/v2/proxy/config/"
_WEBSHARE_LIST_URL = "https://proxy.webshare.io/api/v2/proxy/list/"
_WEBSHARE_PLAN_URL = "https://proxy.webshare.io/api/v2/subscription/plan/"
_WEBSHARE_SUB_URL = "https://proxy.webshare.io/api/v2/subscription/"
_WEBSHARE_STATS_URL = "https://proxy.webshare.io/api/v2/stats/"
_CRED_TTL_SECONDS = 6 * 3600
_LIST_TTL_SECONDS = 90
_STICKY_TTL_SECONDS = 180
_DEAD_TTL_SECONDS = 20 * 60
_GB = 1024**3

_rotating_cache: tuple[float, str] | None = None
_sticky_cache: tuple[float, str] | None = None
_last_sticky_url: str | None = None
_list_cache: tuple[float, list[str]] | None = None
_dead_until: dict[str, float] = {}
_usage_cache: tuple[float, "WebshareUsage"] | None = None
_USAGE_TTL_SECONDS = 120.0


@dataclass(frozen=True)
class WebshareUsage:
    used_bytes: int
    limit_bytes: int
    remaining_bytes: int
    remaining_pct: float
    limit_gb: float
    period_end: str | None = None


def redact_proxy_url(url: str | None) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme or 'http'}://***@{host}{port}"


def httpx_proxy_kwargs(proxy: str | None) -> dict[str, str]:
    text = (proxy or "").strip()
    if not text:
        return {}
    return {"proxy": text}


def html_response_blocked(status: int, text: str) -> bool:
    """Чи відповідь сайту виглядає як блок/капча (тоді варто проксі)."""
    if status in (401, 403, 407, 429, 503):
        return True
    sample = (text or "")[:4000].lower()
    return any(
        marker in sample
        for marker in ("cf-challenge", "just a moment", "captcha", "access denied")
    )


def _explicit_proxy_url() -> str | None:
    for value in (settings.SEARCH_PROXY_URL, settings.OLX_PROXY_URL):
        text = (value or "").strip()
        if text:
            return text
    return None


def _webshare_api_key() -> str:
    return (settings.WEBSHARE_API_KEY or "").strip()


def proxy_configured() -> bool:
    return bool(_explicit_proxy_url() or _webshare_api_key())


def invalidate_sticky_proxy() -> None:
    """Мертвий IP у cooldown, список оновлюємо з API — Webshare часто міняє вузли."""
    global _sticky_cache, _list_cache
    if _last_sticky_url:
        _mark_dead(_last_sticky_url)
    _sticky_cache = None
    _list_cache = None


def is_proxy_tunnel_failure(exc: BaseException | str) -> bool:
    text = str(exc or "").lower()
    return any(
        token in text
        for token in (
            "connect tunnel",
            "tunnel failed",
            "proxy connect",
            "failed to perform",
            "curl: (56)",
            "curl: (7)",
            "curl: (97)",
            "407",
            "proxy authentication",
            "проксі http",
        )
    )


def humanize_proxy_error(error: str) -> str:
    low = (error or "").lower()
    if "connect tunnel" in low or "curl: (56)" in low or "tunnel failed" in low:
        return "тунель CONNECT 502: вузол Webshare не дістався сайту, змінюємо IP"
    if "проксі http 502" in low or "http 502" in low:
        return "проксі повернув 502, змінюємо IP"
    if "407" in low or "proxy authentication" in low:
        return "проксі відхилив авторизацію (407). Перевірте ключ Webshare"
    if "curl: (7)" in low:
        return "проксі Webshare недоступний (немає зʼєднання)"
    text = (error or "").strip()
    return text[:240] if text else "помилка проксі"


def _proxy_url(username: str, password: str, host: str, port: int) -> str:
    user = quote(username, safe="")
    secret = quote(password, safe="")
    return f"http://{user}:{secret}@{host}:{int(port)}"


def _country_code() -> str:
    raw = (settings.WEBSHARE_PROXY_COUNTRY or "UA").strip() or "UA"
    return raw.lower()


def _cache_get(cache: tuple[float, Any] | None, ttl: float) -> Any | None:
    if cache and time.monotonic() - cache[0] < ttl:
        return cache[1]
    return None


def _proxy_mode() -> str:
    raw = (getattr(settings, "WEBSHARE_PROXY_MODE", None) or "direct").strip().lower()
    return "rotate" if raw in {"rotate", "rotating", "backbone"} else "direct"


def _mark_dead(url: str) -> None:
    if not url:
        return
    _dead_until[url] = time.monotonic() + _DEAD_TTL_SECONDS
    logger.info("Webshare proxy cooldown %s", redact_proxy_url(url))


def _cooldown_set() -> set[str]:
    now = time.monotonic()
    for url, until in list(_dead_until.items()):
        if until <= now:
            _dead_until.pop(url, None)
    return set(_dead_until)


def _pick_direct_url(
    urls: list[str],
    *,
    exclude: set[str] | None = None,
    allow_blocked: bool = False,
) -> str | None:
    blocked = exclude or set()
    pool = [item for item in urls if item and item not in blocked]
    if not pool and allow_blocked:
        pool = [item for item in urls if item]
    return random.choice(pool) if pool else None


async def resolve_search_proxy_url(*, sticky: bool = False) -> str | None:
    """Direct Proxy List (IP:port). Rotate-endpoint — лише якщо список порожній."""
    global _sticky_cache, _last_sticky_url
    explicit = _explicit_proxy_url()
    if explicit:
        return explicit
    if not _webshare_api_key():
        return None

    blocked = _cooldown_set()
    if sticky:
        cached = _cache_get(_sticky_cache, _STICKY_TTL_SECONDS)
        if cached and cached not in blocked:
            return cached
        if _last_sticky_url:
            blocked.add(_last_sticky_url)

    chosen: str | None = None
    if _proxy_mode() == "direct":
        urls = await _webshare_direct_urls()
        chosen = _pick_direct_url(urls, exclude=blocked)
        if not chosen:
            urls = await _webshare_direct_urls(force=True)
            chosen = _pick_direct_url(urls, exclude=blocked)
        if chosen:
            live = sum(1 for item in urls if item not in blocked)
            logger.debug(
                "Webshare direct proxy %s live=%s/%s",
                redact_proxy_url(chosen),
                live,
                len(urls),
            )
    if not chosen:
        rotating = await _webshare_rotating_url()
        chosen = rotating
        if rotating and sticky:
            parsed = urlparse(rotating)
            user = parsed.username or ""
            if user.endswith("-rotate"):
                user = user[: -len("-rotate")]
            sid = random.randint(10_000, 99_999_999)
            chosen = _proxy_url(
                f"{user}-{sid}",
                parsed.password or "",
                parsed.hostname or "p.webshare.io",
                parsed.port or 80,
            )
    if sticky and chosen:
        _sticky_cache = (time.monotonic(), chosen)
        _last_sticky_url = chosen
    return chosen


async def _webshare_rotating_url() -> str | None:
    global _rotating_cache
    cached = _cache_get(_rotating_cache, _CRED_TTL_SECONDS)
    if cached:
        return cached

    payload = await _webshare_json("GET", _WEBSHARE_CONFIG_URL)
    if not isinstance(payload, dict):
        return None
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "").strip()
    if not username or not password:
        return None
    country = _country_code()
    url = _proxy_url(f"{username}-{country}-rotate", password, "p.webshare.io", 80)
    _rotating_cache = (time.monotonic(), url)
    logger.info("Webshare rotating proxy ready country=%s", country.upper())
    return url


async def _webshare_direct_urls(*, force: bool = False) -> list[str]:
    global _list_cache
    if not force:
        cached = _cache_get(_list_cache, _LIST_TTL_SECONDS)
        if cached:
            return list(cached)

    country = _country_code()
    payload = await _webshare_json(
        "GET",
        _WEBSHARE_LIST_URL,
        params={
            "mode": "direct",
            "page": 1,
            "page_size": 100,
            "country_code__in": country.upper(),
        },
    )
    if not isinstance(payload, dict) or not payload.get("results"):
        payload = await _webshare_json(
            "GET",
            _WEBSHARE_LIST_URL,
            params={"mode": "direct", "page": 1, "page_size": 100},
        )
    if not isinstance(payload, dict) or not payload.get("results"):
        payload = await _webshare_json(
            "GET",
            _WEBSHARE_LIST_URL,
            params={"mode": "backbone", "page": 1, "page_size": 20},
        )
    if not isinstance(payload, dict):
        return []
    urls: list[str] = []
    for row in payload.get("results") or []:
        if not isinstance(row, dict) or row.get("valid") is False:
            continue
        row_country = str(row.get("country_code") or "").strip().lower()
        if row_country and row_country != country:
            continue
        host = str(row.get("proxy_address") or "").strip()
        if not host or host == "p.webshare.io":
            continue
        port = row.get("port") or 80
        username = str(row.get("username") or "").strip()
        password = str(row.get("password") or "").strip()
        if not username or not password:
            continue
        urls.append(_proxy_url(username, password, host, int(port)))
    if urls:
        _list_cache = (time.monotonic(), urls)
        logger.info("Webshare Proxy List loaded count=%s country=%s", len(urls), country.upper())
    return list(urls)


async def fetch_webshare_usage() -> WebshareUsage | None:
    """Фактичний трафік за цикл (без projected). Кеш 2 хв, щоб не дергати stats."""
    global _usage_cache
    cached = _cache_get(_usage_cache, _USAGE_TTL_SECONDS)
    if cached:
        return cached
    if not _webshare_api_key():
        return None

    plan_payload = await _webshare_json("GET", _WEBSHARE_PLAN_URL)
    limit_gb = _active_bandwidth_limit_gb(plan_payload)
    if limit_gb is None:
        return None

    sub = await _webshare_json("GET", _WEBSHARE_SUB_URL)
    start = ""
    end = None
    if isinstance(sub, dict):
        start = str(sub.get("start_date") or "").strip()
        end = str(sub.get("end_date") or "").strip() or None

    params: dict[str, str] = {}
    if start:
        params["timestamp__gte"] = start
    params["timestamp__lte"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats = await _webshare_json("GET", _WEBSHARE_STATS_URL, params=params or None)
    used = _sum_actual_bandwidth(stats)
    limit_bytes = int(limit_gb * _GB)
    remaining = max(limit_bytes - used, 0)
    pct = 100.0 if limit_bytes <= 0 else remaining / limit_bytes * 100.0
    usage = WebshareUsage(
        used_bytes=used,
        limit_bytes=limit_bytes,
        remaining_bytes=remaining,
        remaining_pct=pct,
        limit_gb=limit_gb,
        period_end=end,
    )
    _usage_cache = (time.monotonic(), usage)
    return usage


def _active_bandwidth_limit_gb(payload: Any) -> float | None:
    rows: list[dict] = []
    if isinstance(payload, dict):
        raw = payload.get("results")
        if isinstance(raw, list):
            rows = [row for row in raw if isinstance(row, dict)]
        elif payload.get("bandwidth_limit") is not None:
            rows = [payload]
    elif isinstance(payload, list):
        rows = [row for row in payload if isinstance(row, dict)]
    active = next((row for row in rows if str(row.get("status") or "") == "active"), None)
    row = active or (rows[0] if rows else None)
    if not row:
        return None
    try:
        return float(row.get("bandwidth_limit") or 0)
    except (TypeError, ValueError):
        return None


def _sum_actual_bandwidth(stats: Any) -> int:
    rows = stats if isinstance(stats, list) else []
    total = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("is_projected"):
            continue
        try:
            total += int(row.get("bandwidth_total") or 0)
        except (TypeError, ValueError):
            continue
    return total


def format_bytes_gb(value: int) -> str:
    return f"{value / _GB:.2f} ГБ"


async def _webshare_json(
    method: str,
    url: str,
    *,
    params: dict | None = None,
) -> Any | None:
    key = _webshare_api_key()
    if not key:
        return None
    headers = {"Authorization": f"Token {key}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(method, url, headers=headers, params=params)
        if response.status_code == 400:
            logger.info(
                "Webshare %s not available",
                (params or {}).get("mode") or url.rsplit("/", 2)[-2],
            )
            return None
        response.raise_for_status()
        return response.json()
    except Exception:
        logger.warning("Webshare API request failed url=%s", url, exc_info=True)
        return None
