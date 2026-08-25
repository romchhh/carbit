"""Розширений пошук: AUTO.RIA params, post-filter, schema."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import SearchFilters
from app.services.search.advanced_filters import (
    advanced_filters_active,
    extract_listing_doors,
    extract_listing_body_label,
    listing_matches_advanced_filters,
)
from app.services.listings.engine_volume import extract_listing_engine_volume


def _item(**kwargs):
    from app.schemas.schemas import ListingOut

    base = dict(
        id="auto_ria_99",
        source="auto_ria",
        title="Toyota Camry 2.5 седан",
        brand="Toyota",
        model="Camry",
        year=2020,
        price=18000,
        currency="USD",
        mileage=55000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description="Торг. Один власник. Без ДТП. 5 дверей.",
        images=[],
        url="https://auto.ria.com/1",
        seller_type="private",
        vin_checked=True,
        source_data={
            "autoData": {
                "seats": 5,
                "door": 4,
                "bodyName": "Седан",
            }
        },
        price_history=[],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class AdvancedSearchSchemaTests(unittest.TestCase):
    def test_accepts_extended_payload(self):
        raw = {
            "brand": "Toyota",
            "body_types": ["Седан"],
            "doors_from": 4,
            "doors_to": 5,
            "seller_filter": "private",
            "accident": "none",
            "zero_mileage": False,
            "bargain": True,
            "vin_verified": True,
            "owners_max": 2,
            "in_credit": "hide",
            "usa_import": "hide",
            "not_customs": "hide",
            "metallic": False,
            "power_unit": "hp",
            "power_from": 150,
            "power_to": 250,
            "seats_from": 5,
            "seats_to": 5,
            "drivetrain": ["Передній"],
            "colors": ["Білий"],
        }
        f = SearchFilters.model_validate(raw)
        self.assertEqual(f.body_types, ["Седан"])
        self.assertEqual(f.seller_filter, "private")
        self.assertTrue(advanced_filters_active(f))


class AdvancedSearchPostFilterTests(unittest.TestCase):
    def test_doors_and_body_and_seller(self):
        item = _item()
        self.assertEqual(extract_listing_doors(item), 4)
        ok = SearchFilters(
            body_types=["Седан"],
            doors_from=4,
            doors_to=5,
            seller_filter="private",
            bargain=True,
            vin_verified=True,
        )
        self.assertTrue(listing_matches_advanced_filters(item, ok))

    def test_rejects_dealer_when_private_wanted(self):
        item = _item(seller_type="dealer")
        self.assertFalse(
            listing_matches_advanced_filters(
                item,
                SearchFilters(seller_filter="private"),
            )
        )

    def test_accident_none_rejects_dtp_text(self):
        item = _item(source="olx", description="Після ДТП, потребує ремонту")
        self.assertFalse(
            listing_matches_advanced_filters(item, SearchFilters(accident="none"))
        )

    def test_accident_auto_ria_rejects_dtp_text(self):
        item = _item(
            source="auto_ria",
            description="Після ДТП, потребує ремонту",
            source_data={"autoData": {}},
        )
        self.assertFalse(
            listing_matches_advanced_filters(item, SearchFilters(accident="none"))
        )

    def test_zero_mileage(self):
        item = _item(mileage=0)
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(zero_mileage=True))
        )
        self.assertFalse(
            listing_matches_advanced_filters(_item(mileage=10000), SearchFilters(zero_mileage=True))
        )

    def test_engine_volume_applies_when_known(self):
        item = _item(source_data={"autoData": {"engineVolume": 2.0}})
        self.assertEqual(extract_listing_engine_volume(item), 2.0)
        ok = SearchFilters(engine_volume_from=1.8, engine_volume_to=2.2)
        bad = SearchFilters(engine_volume_from=2.5, engine_volume_to=3.0)
        self.assertTrue(listing_matches_advanced_filters(item, ok))
        self.assertFalse(listing_matches_advanced_filters(item, bad))

    def test_engine_volume_from_description_bare(self):
        item = _item(
            title="Volkswagen Passat",
            description="Продам авто, двигун 2.0, один власник",
            source_data={"autoData": {}},
        )
        self.assertEqual(extract_listing_engine_volume(item), 2.0)
        self.assertTrue(
            listing_matches_advanced_filters(
                item,
                SearchFilters(engine_volume_from=1.8, engine_volume_to=2.2),
            )
        )
        self.assertFalse(
            listing_matches_advanced_filters(
                item,
                SearchFilters(engine_volume_from=2.5, engine_volume_to=3.0),
            )
        )

    def test_engine_volume_from_title_decimal(self):
        item = _item(
            title="Toyota Camry 2.5 AT",
            description="",
            source_data={"autoData": {}},
        )
        self.assertEqual(extract_listing_engine_volume(item), 2.5)

    def test_engine_volume_passes_when_unknown(self):
        item = _item(source_data={"autoData": {}})
        self.assertIsNone(extract_listing_engine_volume(item))
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(engine_volume_from=2.0, engine_volume_to=3.0))
        )

    def test_body_type_passes_when_unknown(self):
        item = _item(source_data={"autoData": {}}, title="Toyota Camry")
        self.assertIsNone(extract_listing_body_label(item))
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(body_types=["Седан"])))

    def test_body_type_rejects_when_known_mismatch(self):
        item = _item(source_data={"autoData": {"subCategoryName": "Хетчбек"}})
        self.assertEqual(extract_listing_body_label(item), "хетчбек")
        self.assertFalse(listing_matches_advanced_filters(item, SearchFilters(body_types=["Седан"])))


class AutoRiaExtendedParamsTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_extended_api_params(self):
        from app.services.auto_ria.mapper import filters_to_search_params

        client = object()
        filters = SearchFilters(
            brand="Toyota",
            body_types=["Седан", "Універсал"],
            doors_from=4,
            doors_to=5,
            colors=["Білий"],
            metallic=True,
            power_from=150,
            power_to=300,
            power_unit="hp",
            engine_volume_from=1.8,
            engine_volume_to=2.5,
            accident="none",
            seller_filter="private",
            bargain=True,
            vin_verified=True,
            in_credit="hide",
            zero_mileage=True,
        )
        with (
            patch(
                "app.services.auto_ria.mapper.resolve_mark_id",
                AsyncMock(return_value=1),
            ),
            patch(
                "app.services.auto_ria.mapper.resolve_model_id",
                AsyncMock(return_value=0),
            ),
        ):
            params = await filters_to_search_params(
                client,  # type: ignore[arg-type]
                filters,
                page=1,
                per_page=20,
            )

        self.assertEqual(params.get("doorFrom"), 4)
        self.assertEqual(params.get("doorTo"), 5)
        self.assertIn("bodystyle[0]", params)
        self.assertIn("color_id[0]", params)
        self.assertEqual(params.get("metallic"), 1)
        self.assertEqual(params.get("powerFrom"), 150)
        self.assertEqual(params.get("engineVolumeFrom"), 1.8)
        self.assertEqual(params.get("engineVolumeTo"), 2.5)
        self.assertEqual(params.get("power_name"), 1)
        self.assertEqual(params.get("damage"), 1)
        self.assertEqual(params.get("company_type"), 1)
        self.assertEqual(params.get("bargain"), 1)
        self.assertEqual(params.get("checked_VIN"), 1)
        self.assertEqual(params.get("under_credit"), 2)
        self.assertEqual(params.get("raceFrom"), 0)
        self.assertEqual(params.get("raceTo"), 0)


if __name__ == "__main__":
    unittest.main()
