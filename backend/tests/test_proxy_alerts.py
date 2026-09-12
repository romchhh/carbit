from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.search.http_proxy import WebshareUsage
from app.services.search.proxy_alerts import check_webshare_alerts


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
