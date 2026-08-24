from __future__ import annotations

import re

import pytest

from app.core.text import norm_text
from app.services.imperiya.catalog import _carbit_region_key
from app.services.reono.region_paths import resolve_reono_region_segments
from app.services.search.source_error import error_parts, http_request_label
from app.services.reono.errors import ReonoError

UKRAINE_UI_REGIONS = [
    "Вся Україна",
    "м. Київ",
    "Київська область",
    "Вінницька область",
    "Волинська область",
    "Дніпропетровська область",
    "Донецька область",
    "Житомирська область",
    "Закарпатська область",
    "Запорізька область",
    "Івано-Франківська область",
    "Кіровоградська область",
    "Луганська область",
    "Львівська область",
    "Миколаївська область",
    "Одеська область",
    "Полтавська область",
    "Рівненська область",
    "Сумська область",
    "Тернопільська область",
    "Харківська область",
    "Херсонська область",
    "Хмельницька область",
    "Черкаська область",
    "Чернівецька область",
    "Чернігівська область",
]

_LATIN_SLUG = re.compile(r"^[a-z0-9-]+$")


@pytest.mark.parametrize("region", UKRAINE_UI_REGIONS)
def test_reono_region_segments_for_ui_labels(region: str) -> None:
    segments = resolve_reono_region_segments(region)
    if region == "Вся Україна":
        assert segments == []
        return
    assert segments, f"no REONO path for {region!r}"
    for segment in segments:
        assert _LATIN_SLUG.match(segment), segment


@pytest.mark.parametrize(
    ("region", "expected"),
    [
        ("м. Київ", "київ"),
        ("Київська область", "київська"),
        ("Донецька область", "донецька"),
        ("Хмельницька область", "хмельницька"),
    ],
)
def test_imperiya_carbit_region_key(region: str, expected: str) -> None:
    assert _carbit_region_key(region) == norm_text(expected)


def test_http_request_label_with_params() -> None:
    label = http_request_label("GET", "https://api.example/cars", params={"page": 1, "brand": "Audi"})
    assert label.startswith("GET https://api.example/cars?")
    assert "page=1" in label
    assert "brand=Audi" in label


def test_error_parts_includes_request() -> None:
    exc = ReonoError("REONO: помилка 404", request="GET https://reono.ua/legkovoe-avto/kiev/audi/a5")
    msg, req = error_parts(exc)
    assert msg == "REONO: помилка 404"
    assert req == "GET https://reono.ua/legkovoe-avto/kiev/audi/a5"
