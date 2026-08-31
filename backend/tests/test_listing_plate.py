"""Тести витягування держномерів."""

from __future__ import annotations

import unittest

from app.core.timezone import now_kyiv
from app.schemas.schemas import ListingOut
from app.services.listings.plate import (
    enrich_listing_plate,
    extract_plate_from_text,
    normalize_ua_plate,
    plate_from_olx_params,
    resolve_listing_plate,
)


def _listing(**kwargs) -> ListingOut:
    base = dict(
        id="test_1",
        source="telegram",
        title="Zeekr 001",
        brand="Zeekr",
        model="001",
        year=2024,
        price=42000,
        currency="USD",
        mileage=16000,
        fuel="електро",
        transmission="автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://example.com",
        seller_type="private",
        price_history=[],
        is_duplicate=False,
        published_at=now_kyiv(),
        found_at=now_kyiv(),
    )
    base.update(kwargs)
    return ListingOut(**base)


class ListingPlateTests(unittest.TestCase):
    def test_normalize_compact(self):
        self.assertEqual(normalize_ua_plate("BX5318YA"), "BX 5318 YA")
        self.assertEqual(normalize_ua_plate("bx 5318 ya"), "BX 5318 YA")

    def test_extract_from_description(self):
        text = "Продаю Zeekr 001, номер BX 5318 YA, один власник"
        self.assertEqual(extract_plate_from_text(text), "BX 5318 YA")

    def test_auto_ria_source_data(self):
        listing = _listing(
            source="auto_ria",
            source_data={"plateNumber": "KA0007XB"},
        )
        self.assertEqual(resolve_listing_plate(listing), "KA 0007 XB")

    def test_enrich_sets_top_level_field(self):
        listing = enrich_listing_plate(
            _listing(description="Госномер AA1234BC, без ДТП")
        )
        self.assertEqual(listing.plate, "AA 1234 BC")

    def test_invalid_not_matched(self):
        self.assertIsNone(normalize_ua_plate("12345"))
        self.assertIsNone(extract_plate_from_text("Toyota Camry 2020"))

    def test_imperiya_nested_source_data(self):
        listing = _listing(
            source="imperiya",
            source_data={"imperiya": {"plateNumber": "BC1070HX"}},
        )
        self.assertEqual(resolve_listing_plate(listing), "BC 1070 HX")

    def test_olx_license_plate_param(self):
        listing = _listing(
            source="olx",
            source_data={
                "raw_params": {
                    "params": [
                        {
                            "key": "license_plate",
                            "name": "Держ. номер реєстрації",
                            "value": {"key": "BC1070HX", "label": "BC1070HX "},
                        }
                    ]
                }
            },
        )
        self.assertEqual(resolve_listing_plate(listing), "BC 1070 HX")

    def test_olx_cyrillic_plate_param(self):
        plate = plate_from_olx_params(
            [
                {
                    "key": "license_plate",
                    "value": {"key": "ВХ8376ЕХ"},
                }
            ]
        )
        self.assertEqual(plate, "BX 8376 EX")

    def test_reono_nested_source_data(self):
        listing = _listing(
            source="reono",
            source_data={"reono": {"plateNumber": "AA2459TP"}},
        )
        self.assertEqual(resolve_listing_plate(listing), "AA 2459 TP")


if __name__ == "__main__":
    unittest.main()
