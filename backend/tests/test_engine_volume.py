"""Тести визначення обʼєму двигуна."""

from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.listings.engine_volume import extract_listing_engine_volume, listing_engine_volume_in_range
from app.services.search.advanced_filters import listing_matches_advanced_filters


def _item(**kwargs) -> ListingOut:
    base = dict(
        id="x1",
        source="olx",
        title="Test car",
        brand="VW",
        model="Passat",
        year=2019,
        price=10000,
        currency="USD",
        mileage=90000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description="",
        images=[],
        url="https://olx.ua/1",
        seller_type="private",
        source_data={},
        price_history=[],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class EngineVolumeExtractTests(unittest.TestCase):
    def test_structured_auto_ria(self):
        item = _item(source_data={"autoData": {"engineVolume": 2.0}})
        self.assertEqual(extract_listing_engine_volume(item), 2.0)

    def test_telegram_source_data(self):
        item = _item(source_data={"engine_volume_l": 1.6})
        self.assertEqual(extract_listing_engine_volume(item), 1.6)

    def test_description_engine_keyword(self):
        item = _item(description="Авто на ходу, двигун 3.0, сервісна книга")
        self.assertEqual(extract_listing_engine_volume(item), 3.0)

    def test_title_with_transmission_hint(self):
        item = _item(title="BMW 530 3.0 AT", description="")
        self.assertEqual(extract_listing_engine_volume(item), 3.0)

    def test_title_trailing_decimal(self):
        item = _item(title="Toyota Camry 2.5", description="")
        self.assertEqual(extract_listing_engine_volume(item), 2.5)

    def test_cm3_volume(self):
        item = _item(description="Обʼєм 1998 см3, бензин")
        self.assertEqual(extract_listing_engine_volume(item), 2.0)

    def test_olx_specs_key(self):
        item = _item(source_data={"specs": {"Обʼєм двигуна": "2.0 л"}})
        self.assertEqual(extract_listing_engine_volume(item), 2.0)

    def test_filter_rejects_known_mismatch(self):
        item = _item(title="Skoda Octavia 1.6 TSI")
        filters = SearchFilters(engine_volume_from=2.0, engine_volume_to=3.0)
        self.assertFalse(listing_matches_advanced_filters(item, filters))
        self.assertFalse(
            listing_engine_volume_in_range(item, volume_from=2.0, volume_to=3.0),
        )

    def test_filter_passes_unknown(self):
        item = _item(title="Renault Megane", description="без опису двигуна")
        filters = SearchFilters(engine_volume_from=2.0, engine_volume_to=3.0)
        self.assertTrue(listing_matches_advanced_filters(item, filters))

    def test_fuel_before_decimal(self):
        item = _item(title="BMW X5", description="бензин 3.0, автомат")
        self.assertEqual(extract_listing_engine_volume(item), 3.0)

    def test_fuel_after_decimal(self):
        item = _item(title="Audi A6 3.0 дизель", description="")
        self.assertEqual(extract_listing_engine_volume(item), 3.0)

    def test_diesel_comma_decimal(self):
        item = _item(description="Дизель 2,99 л, 4WD")
        self.assertEqual(extract_listing_engine_volume(item), 2.99)

    def test_auto_ria_fuel_name_integer_litres(self):
        item = _item(
            fuel="Бензин",
            source_data={"autoData": {"fuelName": "Бензин, 3 л.", "engineVolume": None}},
        )
        self.assertEqual(extract_listing_engine_volume(item), 3.0)

    def test_auto_ria_fuel_name_diesel(self):
        item = _item(
            fuel="Дизель",
            source_data={"autoData": {"fuelName": "Дизель, 2.99 л.", "engineVolume": None}},
        )
        self.assertEqual(extract_listing_engine_volume(item), 2.99)

    def test_auto_ria_new_main_params_volume_cm3(self):
        item = _item(
            source="auto_ria",
            source_data={"mainParams": {"volume": 2487, "fuel": "Гібрид (HEV)"}},
        )
        self.assertEqual(extract_listing_engine_volume(item), 2.49)

    def test_fuel_year_not_volume(self):
        item = _item(title="Volkswagen Passat бензин 2019", description="")
        self.assertIsNone(extract_listing_engine_volume(item))


class NewAutoRiaEngineVolumeTests(unittest.TestCase):
    def test_new_info_to_listing_sets_engine_volume_from_cm3(self):
        from app.services.auto_ria.mapper import new_info_to_listing

        listing = new_info_to_listing(
            {
                "autoId": 2082780,
                "marka": "Toyota",
                "model": "RAV4",
                "year": 2025,
                "priceUsd": 42000,
                "priceUah": 0,
                "mainParams": {
                    "fuel": "Гібрид (HEV)",
                    "gear": "Варіатор",
                    "volume": 2487,
                },
                "salon": {"city": "Київ"},
                "photos": [],
                "note": "Новий RAV4",
            }
        )
        self.assertEqual(listing.engine_volume_l, 2.49)
        self.assertEqual(listing.source_data.get("mainParams", {}).get("volume"), 2487)
