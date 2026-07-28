from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.admin.api_usage import (
    auto_ria_operation,
    build_api_usage_report,
    olx_operation,
    record_api_request,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/auto/search", "search"),
        ("/auto/info", "info"),
        ("/auto/fotos/12345", "fotos"),
        ("/auto/categories/1/marks", "catalog"),
    ],
)
def test_auto_ria_operation(path: str, expected: str) -> None:
    assert auto_ria_operation(path) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.olx.ua/api/v1/offers", "search"),
        ("https://www.olx.ua/d/uk/obyavlenie/test-ID.html", "details"),
        ("https://www.olx.ua/transport/", "html"),
    ],
)
def test_olx_operation(url: str, expected: str) -> None:
    assert olx_operation(url) == expected


@pytest.mark.asyncio
async def test_record_and_report_api_usage() -> None:
    redis = MagicMock()
    stored: dict[str, dict[str, int]] = {}

    async def hincrby(key, field, amount):
        stored.setdefault(key, {})
        stored[key][field] = stored[key].get(field, 0) + amount

    pipe = MagicMock()
    pipe.hincrby = MagicMock(side_effect=lambda key, field, amount: hincrby(key, field, amount))
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[])

    redis.pipeline = MagicMock(return_value=pipe)

    with patch("app.services.admin.api_usage.get_redis", AsyncMock(return_value=redis)):
        await record_api_request("auto_ria", "search", success=True, count=2)
        await record_api_request("olx", "html", success=False)

    assert any(k.startswith("api_usage:hour:auto_ria:") for k in stored)
    hour_key = next(k for k in stored if k.startswith("api_usage:hour:auto_ria:"))
    assert stored[hour_key]["total"] == 2
    assert stored[hour_key]["ok"] == 2
    assert stored[hour_key]["op:search"] == 2

    async def hgetall(key):
        return stored.get(key, {})

    redis.hgetall = AsyncMock(side_effect=hgetall)

    with patch("app.services.admin.api_usage.get_redis", AsyncMock(return_value=redis)):
        report = await build_api_usage_report(hours=6, days=3)

    assert "auto_ria" in report["sources"]
    assert report["sources"]["auto_ria"]["today_total"] >= 2
    assert report["sources"]["auto_ria"]["period_total"] >= 2
    assert report["days_window"] == 3
