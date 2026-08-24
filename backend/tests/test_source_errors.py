"""Тести помилок і моніторингу для всіх джерел пошуку."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.schemas import SourceStatusOut
from app.services.auto_ria.client import AutoRiaError
from app.services.car_market.errors import CarMarketError
from app.services.imperiya.errors import ImperiyaError
from app.services.monitoring.catalog import PARSER_LABELS, WEB_PARSER_SOURCES
from app.services.monitoring.collect import _check_parser
from app.services.monitoring.models import ComponentStatus, HealthLevel, SystemStatus
from app.services.monitoring.parser_status import is_benign_parser_error, normalize_parser_source
from app.services.olx.errors import OlxError
from app.services.reono.errors import ReonoError
from app.services.search.multi_source import SourceSearchStatus, _failed_source_status
from app.services.search.search_endpoint import _outcome_sources
from app.services.search.source_error import error_parts
from app.services.udrive.errors import UdriveError

SOURCE_404_CASES = [
    ("AUTO.RIA", "AUTO.RIA: помилка 404"),
    ("OLX", "OLX: помилка 404"),
    ("Імперія Авто", "Імперія Авто: помилка 404"),
    ("uDrive", "uDrive: помилка 404"),
    ("Car Market", "Car Market: помилка 404"),
    ("REONO", "REONO: помилка 404"),
    ("Telegram", "Telegram: не знайдено"),
]

SOURCE_HARD_ERROR_CASES = [
    ("AUTO.RIA", "AUTO.RIA: мережева помилка"),
    ("OLX", "OLX: таймаут"),
    ("Імперія Авто", "Імперія Авто: помилка 503"),
    ("uDrive", "uDrive: мережева помилка"),
    ("Car Market", "Car Market: помилка 502"),
    ("REONO", "REONO: мережева помилка"),
]

ERROR_WITH_REQUEST_CASES = [
    (
        ReonoError,
        "REONO",
        "REONO: помилка 404",
        "GET https://reono.ua/legkovoe-avto/kiev/audi/a5",
    ),
    (
        CarMarketError,
        "Car Market",
        "Car Market: помилка 404",
        "GET https://car-market.ua/api/cars?page=1",
    ),
    (
        ImperiyaError,
        "Імперія Авто",
        "Імперія Авто: помилка 404",
        "GET https://api.imperiya.ua/api/v2/cars?regionId=1",
    ),
    (
        UdriveError,
        "uDrive",
        "uDrive: помилка 404",
        "GET https://api.udrive.com.ua/query-aggregator/cars/query",
    ),
]


@pytest.mark.parametrize("message", [case[1] for case in SOURCE_404_CASES])
def test_benign_parser_error_accepts_404_for_all_sources(message: str) -> None:
    assert is_benign_parser_error(message) is True


@pytest.mark.parametrize("message", [case[1] for case in SOURCE_HARD_ERROR_CASES])
def test_benign_parser_error_rejects_real_failures(message: str) -> None:
    assert is_benign_parser_error(message) is False


@pytest.mark.parametrize("exc_cls,source,message,request_label", ERROR_WITH_REQUEST_CASES)
def test_error_parts_for_all_http_sources(
    exc_cls: type[Exception],
    source: str,
    message: str,
    request_label: str,
) -> None:
    exc = exc_cls(message, request=request_label)
    msg, req = error_parts(exc)
    assert msg == message
    assert req == request_label

    status = _failed_source_status(source, exc)
    assert status.error == message
    assert status.request == request_label


def test_failed_source_status_for_string_error_without_request() -> None:
    status = _failed_source_status("OLX", "OLX: таймаут")
    assert status.error == "OLX: таймаут"
    assert status.request is None


def test_failed_source_status_for_auto_ria_without_request_attr() -> None:
    exc = AutoRiaError("AUTO.RIA: помилка 500")
    status = _failed_source_status("AUTO.RIA", exc)
    assert status.error == "AUTO.RIA: помилка 500"
    assert status.request is None


def test_outcome_sources_maps_request_for_all_sources() -> None:
    statuses = [
        SourceSearchStatus(
            source=label,
            item_count=0,
            error=f"{label}: помилка 404",
            request=f"GET https://example.test/{key}",
        )
        for key, label in PARSER_LABELS.items()
    ]
    out = _outcome_sources(statuses)
    assert len(out) == len(PARSER_LABELS)
    for row in out:
        assert isinstance(row, SourceStatusOut)
        assert row.error and "404" in row.error
        assert row.request and row.request.startswith("GET https://example.test/")


@pytest.mark.parametrize("source_key", WEB_PARSER_SOURCES)
def test_check_parser_benign_404_is_ok_for_all_web_sources(source_key: str) -> None:
    label = PARSER_LABELS[source_key]
    payload = {
        "ok": False,
        "error": f"{label}: помилка 404",
        "count": 0,
        "at": time.time(),
    }

    async def run() -> ComponentStatus:
        with patch(
            "app.services.monitoring.collect.get_parser_status",
            new=AsyncMock(return_value=payload),
        ):
            return await _check_parser(source_key)

    comp = asyncio.run(run())

    assert comp.level == HealthLevel.OK
    assert comp.component_id == f"parser:{source_key}"
    assert "OK" in comp.detail


@pytest.mark.parametrize("source_key", WEB_PARSER_SOURCES)
def test_check_parser_hard_error_is_degraded_not_down(source_key: str) -> None:
    label = PARSER_LABELS[source_key]
    payload = {
        "ok": False,
        "error": f"{label}: мережева помилка",
        "count": 0,
        "at": time.time(),
    }

    async def run() -> ComponentStatus:
        with patch(
            "app.services.monitoring.collect.get_parser_status",
            new=AsyncMock(return_value=payload),
        ):
            return await _check_parser(source_key)

    comp = asyncio.run(run())

    assert comp.level == HealthLevel.DEGRADED
    assert comp.level != HealthLevel.DOWN


@pytest.mark.parametrize("source_key", WEB_PARSER_SOURCES)
def test_single_parser_degraded_does_not_mark_system_down(source_key: str) -> None:
    label = PARSER_LABELS[source_key]
    status = SystemStatus(
        components=[
            ComponentStatus("backend", "Backend API", HealthLevel.OK, "OK"),
            ComponentStatus("frontend", "Frontend", HealthLevel.OK, "HTTP 200"),
            ComponentStatus("bot", "Telegram бот", HealthLevel.OK, "heartbeat"),
            ComponentStatus("worker", "Worker (парсер)", HealthLevel.OK, "heartbeat"),
            ComponentStatus("telegram_parser", "Telegram парсер", HealthLevel.OK, "OK"),
            ComponentStatus(
                f"parser:{source_key}",
                label,
                HealthLevel.DEGRADED,
                f"{label}: помилка 404",
            ),
        ],
        checked_at=time.time(),
    )
    assert status.overall == HealthLevel.DEGRADED
    assert status.overall != HealthLevel.DOWN


@pytest.mark.parametrize("canonical", list(PARSER_LABELS))
def test_normalize_parser_source_for_all_labels(canonical: str) -> None:
    label = PARSER_LABELS[canonical]
    assert normalize_parser_source(label) == canonical
    assert normalize_parser_source(canonical) == canonical


def test_olx_error_without_request_still_works() -> None:
    exc = OlxError("OLX: помилка 404", status_code=404)
    status = _failed_source_status("OLX", exc)
    assert status.error == "OLX: помилка 404"
    assert status.request is None
    assert is_benign_parser_error(status.error) is True
