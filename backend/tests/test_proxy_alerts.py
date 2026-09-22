from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.search.http_proxy import WebshareUsage
from app.services.search.proxy_alerts import (
    _fail_alert_key,
    _mark_once,
    check_webshare_alerts,
    notify_proxy_problem,
)


def _usage(*, remaining_pct: float, remaining_bytes: int, used: int = 1, limit_gb: float = 3) -> WebshareUsage:
    limit = int(limit_gb * 1024**3)
    return WebshareUsage(
        used_bytes=used,
        limit_bytes=limit,
        remaining_bytes=remaining_bytes,
        remaining_pct=remaining_pct,
        limit_gb=limit_gb,
        period_end="2026-10-12T11:42:23.943662Z",
    )


def test_fail_alert_key_dedupes_html_errors():
    assert _fail_alert_key("AUTO.RIA", "direct і проксі не віддали HTML") == "fail:html_unavailable"
    assert _fail_alert_key("OLX", "AUTO.RIA HTML failed") == "fail:html_unavailable"
    assert _fail_alert_key("OLX", "407 proxy auth") == "fail:olx"


def test_mark_once_is_atomic():
    async def run():
        calls = {"n": 0}

        async def fake_setnx(key, ttl, value):
            calls["n"] += 1
            return calls["n"] == 1

        fake_redis = AsyncMock()
        fake_redis.setnx_ex = fake_setnx

        with patch("app.services.search.proxy_alerts.get_redis", new=AsyncMock(return_value=fake_redis)):
            first = await _mark_once("fail:html_unavailable", 60)
            second = await _mark_once("fail:html_unavailable", 60)

        assert first is True
        assert second is False

    asyncio.run(run())


def test_notify_proxy_problem_sends_once_for_parallel_html_failures():
    async def run():
        sent: list[str] = []

        async def fake_notify(text: str) -> None:
            sent.append(text)

        async def fake_mark(key, ttl):
            return key == "fail:html_unavailable" and not sent

        with (
            patch("app.services.search.proxy_alerts._mark_once", new=AsyncMock(side_effect=fake_mark)),
            patch("app.services.search.proxy_alerts.notify_monitor_admins", new=fake_notify),
        ):
            await notify_proxy_problem(source="AUTO.RIA", error="direct і проксі не віддали HTML")
            await notify_proxy_problem(source="AUTO.RIA", error="direct і проксі не віддали HTML")

        assert len(sent) == 1

    asyncio.run(run())


def test_bandwidth_warning_at_20_percent():
    async def run():
        sent: list[str] = []

        async def fake_notify(text: str) -> None:
            sent.append(text)

        with (
            patch("app.services.search.proxy_alerts.proxy_configured", return_value=True),
            patch(
                "app.services.search.proxy_alerts.fetch_webshare_usage",
                new=AsyncMock(return_value=_usage(remaining_pct=18, remaining_bytes=500)),
            ),
            patch("app.services.search.proxy_alerts._mark_once", new=AsyncMock(return_value=True)),
            patch("app.services.search.proxy_alerts.notify_monitor_admins", new=fake_notify),
            patch("app.services.search.proxy_alerts.settings") as fake_settings,
        ):
            fake_settings.WEBSHARE_BANDWIDTH_WARN_REMAINING = "50,20,5"
            await check_webshare_alerts()

        assert sent
        assert "закінчується трафік" in sent[0]
        assert "18%" in sent[0]

    asyncio.run(run())


def test_exhausted_bandwidth_alert():
    async def run():
        sent: list[str] = []

        async def fake_notify(text: str) -> None:
            sent.append(text)

        with (
            patch("app.services.search.proxy_alerts.proxy_configured", return_value=True),
            patch(
                "app.services.search.proxy_alerts.fetch_webshare_usage",
                new=AsyncMock(return_value=_usage(remaining_pct=0, remaining_bytes=0, used=3 * 1024**3)),
            ),
            patch("app.services.search.proxy_alerts._mark_once", new=AsyncMock(return_value=True)),
            patch("app.services.search.proxy_alerts.notify_monitor_admins", new=fake_notify),
            patch("app.services.search.proxy_alerts.settings") as fake_settings,
        ):
            fake_settings.WEBSHARE_BANDWIDTH_WARN_REMAINING = "50,20,5"
            await check_webshare_alerts()

        assert sent
        assert "трафік вичерпано" in sent[0]

    asyncio.run(run())
