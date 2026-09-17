from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.services.udrive.constants import udrive_listing_url
from app.services.udrive.mapper import _parse_udrive_datetime, car_to_listing


def test_udrive_listing_url_without_brand_slug():
    car_id = "2995AB35-8D3F-4289-BABF-FF9D939BCECE"
    assert (
        udrive_listing_url(car_id)
        == "https://udrive.com.ua/catalog/cars/2995ab35-8d3f-4289-babf-ff9d939bcece"
    )


def test_udrive_listing_url_matches_public_site_format():
    assert (
        udrive_listing_url("0490d522-1c2d-48cd-b2cb-7c8f38ac5320")
        == "https://udrive.com.ua/catalog/cars/0490d522-1c2d-48cd-b2cb-7c8f38ac5320"
    )


def test_parse_udrive_published_date_with_7_fraction_digits():
    parsed = _parse_udrive_datetime("2026-04-17T12:49:28.3103896Z")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 4
    assert parsed.day == 17


def test_car_to_listing_uses_published_date():
    listing = car_to_listing(
        {
            "id": "abc",
            "publishedDate": "2026-04-17T12:49:28.3103896Z",
            "createdDate": "2026-04-17T06:39:04.507556Z",
            "model": {"name": "001", "year": 2026, "makeId": 40},
            "price": {"amount": 1},
        },
        makes_by_id={40: {"name": "Zeekr"}},
    )
    assert listing.published_at.year == 2026
    assert listing.published_at.month == 4
    assert listing.published_at.tzinfo is not None
    assert listing.published_at != datetime(1970, 1, 1, tzinfo=KYIV_TZ)


def test_electric_drops_dummy_engine_volume():
    listing = car_to_listing(
        {
            "id": "abc",
            "publishedDate": "2026-04-17T12:49:28.3103896Z",
            "model": {"name": "001", "year": 2026, "makeId": 40},
            "price": {"amount": 61700},
            "specification": {
                "fuel": {"type": "electric"},
                "engine": {"volume": {"l": 2.0, "cm3": 2000}},
            },
        },
        makes_by_id={40: {"name": "Zeekr"}},
    )
    assert listing.fuel == "Електро"
    assert listing.engine_volume_l is None
