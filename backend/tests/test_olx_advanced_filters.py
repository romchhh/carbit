"""Розширені фільтри для OLX (post-filter + advanced_filters)."""

from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.olx.mapper import olx_listing_to_listing_out
from app.services.olx.parser import OlxListing, OlxSearchParams, passes_olx_filters, passes_post_filters
from app.services.search.advanced_filters import (
    extract_listing_doors,
    extract_listing_power_hp,
    listing_matches_advanced_filters,
)


def _olx_specs_listing(**specs: str) -> OlxListing:
    return OlxListing(
        listing_id="1",
        title="BMW 8 Series",
        url="https://www.olx.ua/d/uk/obyavlenie/test-ID1.html",
        price="50000",
        currency="USD",
        year="2020",
        mileage="83 тис.км.",
        specs=dict(specs),
        raw_params={"isBusiness": True},
    )


def _olx_item(**specs: str) -> ListingOut:
    return olx_listing_to_listing_out(_olx_specs_listing(**specs))


class OlxPostFilterTests(unittest.TestCase):
    def test_drivetrain_awd_matches_povniy(self):
        listing = _olx_specs_listing(**{"Тип приводу": "Повний"})
        params = OlxSearchParams(drivetrain="awd")
        self.assertTrue(passes_post_filters(listing, params))
        self.assertTrue(passes_olx_filters(listing, params))

    def test_drivetrain_rejects_mismatch(self):
        listing = _olx_specs_listing(**{"Тип приводу": "Передній"})
        params = OlxSearchParams(drivetrain="awd")
        self.assertFalse(passes_post_filters(listing, params))

    def test_power_range(self):
        listing = _olx_specs_listing(**{"Потужність": "523 к.с."})
        ok = OlxSearchParams(power_from=400, power_to=600)
        bad = OlxSearchParams(power_from=600, power_to=700)
        self.assertTrue(passes_post_filters(listing, ok))
        self.assertFalse(passes_post_filters(listing, bad))

    def test_seats_range(self):
        listing = _olx_specs_listing(**{"Кількість місць": "5"})
        ok = OlxSearchParams(seats_from=5, seats_to=5)
        bad = OlxSearchParams(seats_from=7, seats_to=7)
        self.assertTrue(passes_post_filters(listing, ok))
        self.assertFalse(passes_post_filters(listing, bad))

    def test_fuel_consumption(self):
        listing = _olx_specs_listing(**{"Витрата палива": "7.5 л/100 км"})
        ok = OlxSearchParams(consumption_from=6.0, consumption_to=8.0)
        bad = OlxSearchParams(consumption_from=9.0, consumption_to=12.0)
        self.assertTrue(passes_post_filters(listing, ok))
        self.assertFalse(passes_post_filters(listing, bad))


class OlxAdvancedFilterTests(unittest.TestCase):
    def test_doors_from_specs(self):
        item = _olx_item(**{"Кількість дверей": "4"})
        self.assertEqual(extract_listing_doors(item), 4)
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(doors_from=4, doors_to=5))
        )
        self.assertFalse(
            listing_matches_advanced_filters(item, SearchFilters(doors_from=2, doors_to=3))
        )

    def test_power_from_specs(self):
        item = _olx_item(**{"Потужність": "523 к.с."})
        self.assertEqual(extract_listing_power_hp(item), 523.0)
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(power_from=400, power_to=600))
        )

    def test_drivetrain_advanced(self):
        item = _olx_item(**{"Тип приводу": "Повний"})
        self.assertTrue(
            listing_matches_advanced_filters(item, SearchFilters(drivetrain=["Повний"]))
        )
        self.assertFalse(
            listing_matches_advanced_filters(item, SearchFilters(drivetrain=["Передній"]))
        )

    def test_color_advanced(self):
        item = _olx_item(**{"Kолір": "Чорний"})
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(colors=["Чорний"])))
        self.assertFalse(listing_matches_advanced_filters(item, SearchFilters(colors=["Білий"])))

    def test_body_type_from_specs(self):
        item = _olx_item(**{"Тип кузова": "Купе"})
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(body_types=["Купе"])))
        self.assertFalse(listing_matches_advanced_filters(item, SearchFilters(body_types=["Седан"])))

    def test_seller_dealer_from_is_business(self):
        item = _olx_item(**{"Тип кузова": "Купе"})
        self.assertEqual(item.seller_type, "dealer")
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(seller_filter="dealer")))
        self.assertFalse(listing_matches_advanced_filters(item, SearchFilters(seller_filter="private")))

    def test_usa_import_from_specs(self):
        item = _olx_item(**{"Авто пригнано з": "США"})
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(usa_import="show")))
        self.assertFalse(listing_matches_advanced_filters(item, SearchFilters(usa_import="hide")))

    def test_in_credit_from_sale_terms(self):
        item = _olx_item(**{"Умови продажу": "Кредит, Лізинг"})
        self.assertTrue(listing_matches_advanced_filters(item, SearchFilters(in_credit="show")))


if __name__ == "__main__":
    unittest.main()
