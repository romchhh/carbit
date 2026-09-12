from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.search import http_proxy


def setup_function() -> None:
    http_proxy._list_cache = None
    http_proxy._rotating_cache = None
    http_proxy._sticky_cache = None
    http_proxy._usage_cache = None


def test_redact_proxy_url_hides_credentials():
    assert http_proxy.redact_proxy_url("http://user:secret@p.webshare.io:80") == "http://***@p.webshare.io:80"
    assert http_proxy.redact_proxy_url("") == ""


def test_httpx_proxy_kwargs():
    assert http_proxy.httpx_proxy_kwargs(None) == {}
    assert http_proxy.httpx_proxy_kwargs("http://u:p@host:80") == {"proxy": "http://u:p@host:80"}


def test_explicit_search_proxy_wins():
    async def run():
        with (
            patch.object(http_proxy.settings, "SEARCH_PROXY_URL", "http://a:b@proxy.test:8080"),
            patch.object(http_proxy.settings, "WEBSHARE_API_KEY", "token"),
        ):
            url = await http_proxy.resolve_search_proxy_url()
        assert url == "http://a:b@proxy.test:8080"

    asyncio.run(run())


def test_webshare_sticky_uses_rotating_session():
    async def run():
        with (
            patch.object(http_proxy.settings, "SEARCH_PROXY_URL", ""),
            patch.object(http_proxy.settings, "OLX_PROXY_URL", ""),
            patch.object(http_proxy.settings, "WEBSHARE_API_KEY", "token"),
            patch.object(http_proxy.settings, "WEBSHARE_PROXY_COUNTRY", "UA"),
            patch.object(
                http_proxy,
                "_webshare_json",
                new=AsyncMock(return_value={"username": "demo", "password": "secret"}),
            ),
        ):
            url = await http_proxy.resolve_search_proxy_url(sticky=True)
        assert url.startswith("http://demo-ua-")
        assert url.endswith("@p.webshare.io:80")
        assert "-rotate@" not in url
        assert "secret" in url

    asyncio.run(run())


def test_webshare_direct_list_fallback_when_config_missing():
    async def run():
        payload = {
            "results": [
                {
                    "valid": True,
                    "proxy_address": "82.26.221.27",
                    "port": 5368,
                    "username": "demo",
                    "password": "secret",
                }
            ]
        }
        with (
            patch.object(http_proxy.settings, "SEARCH_PROXY_URL", ""),
            patch.object(http_proxy.settings, "OLX_PROXY_URL", ""),
            patch.object(http_proxy.settings, "WEBSHARE_API_KEY", "token"),
            patch.object(http_proxy, "_webshare_rotating_url", new=AsyncMock(return_value=None)),
            patch.object(http_proxy, "_webshare_json", new=AsyncMock(return_value=payload)),
        ):
            url = await http_proxy.resolve_search_proxy_url(sticky=True)
        assert url == "http://demo:secret@82.26.221.27:5368"

    asyncio.run(run())


def test_webshare_rotating_url_uses_country():
    async def run():
        with (
            patch.object(http_proxy.settings, "SEARCH_PROXY_URL", ""),
            patch.object(http_proxy.settings, "OLX_PROXY_URL", ""),
            patch.object(http_proxy.settings, "WEBSHARE_API_KEY", "token"),
            patch.object(http_proxy.settings, "WEBSHARE_PROXY_COUNTRY", "UA"),
            patch.object(
                http_proxy,
                "_webshare_direct_urls",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                http_proxy,
                "_webshare_json",
                new=AsyncMock(return_value={"username": "demo", "password": "secret"}),
            ),
        ):
            url = await http_proxy.resolve_search_proxy_url(sticky=False)
        assert url == "http://demo-ua-rotate:secret@p.webshare.io:80"

    asyncio.run(run())


def test_html_response_blocked():
    assert http_proxy.html_response_blocked(403, "ok")
    assert http_proxy.html_response_blocked(200, "<html>cf-challenge</html>")
    assert not http_proxy.html_response_blocked(200, "<html>Zeekr 001 Київ</html>")


def test_sum_actual_bandwidth_skips_projected():
    used = http_proxy._sum_actual_bandwidth(
        [
            {"is_projected": False, "bandwidth_total": 1000},
            {"is_projected": True, "bandwidth_total": 999999},
            {"is_projected": False, "bandwidth_total": 500},
        ]
    )
    assert used == 1500


def test_active_bandwidth_limit_prefers_active_plan():
    gb = http_proxy._active_bandwidth_limit_gb(
        {
            "results": [
                {"status": "cancelled", "bandwidth_limit": 1},
                {"status": "active", "bandwidth_limit": 3},
            ]
        }
    )
    assert gb == 3.0
