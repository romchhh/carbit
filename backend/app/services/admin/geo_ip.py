"""Визначення країни відвідувача за IP (без Cloudflare/Vercel)."""

from __future__ import annotations

import ipaddress
import logging
from pathlib import Path

import httpx
from fastapi import Request

from app.core.config import ROOT_DIR, settings
from app.core.redis import get_redis
from app.services.rate_limit import client_ip

logger = logging.getLogger(__name__)

GEO_CACHE_TTL_SECONDS = 60 * 60 * 24 * 14
_MAXMIND_READER = None


def is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_reserved
        or addr.is_link_local
        or addr.is_multicast
    )


def country_from_proxy_headers(request: Request) -> str | None:
    for header in (
        "cf-ipcountry",
        "x-vercel-ip-country",
        "cloudfront-viewer-country",
        "x-country-code",
    ):
        value = (request.headers.get(header) or "").strip().upper()
        if len(value) == 2 and value != "XX":
            return value
    return None


def _geoip_db_path() -> Path | None:
    raw = (settings.GEOIP_COUNTRY_DB or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path if path.is_file() else None


def _maxmind_reader():
    global _MAXMIND_READER
    if _MAXMIND_READER is not None:
        return _MAXMIND_READER

    path = _geoip_db_path()
    if not path:
        return None

    try:
        import geoip2.database
    except ImportError:
        logger.warning(
            "GEOIP_COUNTRY_DB задано (%s), але пакет geoip2 не встановлено",
            path,
        )
        return None

    try:
        _MAXMIND_READER = geoip2.database.Reader(str(path))
        logger.info("GeoIP database loaded: %s", path)
        return _MAXMIND_READER
    except Exception:
        logger.warning("GeoIP database unavailable at %s", path, exc_info=True)
        return None


def country_from_maxmind(ip: str) -> str | None:
    reader = _maxmind_reader()
    if not reader:
        return None
    try:
        response = reader.country(ip)
        code = (response.country.iso_code or "").strip().upper()
        return code if len(code) == 2 else None
    except Exception:
        return None


async def _lookup_country_http(ip: str) -> str | None:
    providers = (
        f"http://ip-api.com/json/{ip}?fields=status,countryCode",
        f"https://ipwho.is/{ip}",
    )
    async with httpx.AsyncClient(timeout=2.5, follow_redirects=True) as client:
        for url in providers:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    continue
                data = response.json()
                if "ip-api.com" in url:
                    if data.get("status") != "success":
                        continue
                    code = (data.get("countryCode") or "").strip().upper()
                else:
                    if not data.get("success", True):
                        continue
                    code = (data.get("country_code") or "").strip().upper()
                if len(code) == 2:
                    return code
            except Exception:
                logger.debug("geo lookup failed url=%s ip=%s", url, ip, exc_info=True)
    return None


async def resolve_country_code(ip: str) -> str:
    normalized = (ip or "").strip()
    if not normalized or normalized == "unknown" or is_private_ip(normalized):
        return "XX"

    cache_key = f"geo:country:{normalized}"
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            code = cached.decode() if isinstance(cached, bytes) else str(cached)
            code = code.strip().upper()
            if len(code) == 2:
                return code
    except Exception:
        pass

    code = country_from_maxmind(normalized)
    if not code:
        code = await _lookup_country_http(normalized)
    if not code:
        code = "XX"

    try:
        redis = await get_redis()
        await redis.setex(cache_key, GEO_CACHE_TTL_SECONDS, code)
    except Exception:
        pass
    return code


async def resolve_visit_country(request: Request) -> str:
    """Країна відвідувача: CDN-заголовки → MaxMind → HTTP lookup за IP."""
    from_header = country_from_proxy_headers(request)
    if from_header:
        return from_header
    return await resolve_country_code(client_ip(request))
