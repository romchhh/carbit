from __future__ import annotations

import unittest

from app.services.auto_ria.mapper import _listing_price_from_info, _parse_money, info_to_listing


class AutoRiaPriceTests(unittest.TestCase):
    def test_parse_spaced_string(self):
        self.assertEqual(_parse_money("12 500"), 12_500)
        self.assertEqual(_parse_money("557\u00a0500"), 557_500)
        self.assertEqual(_parse_money(12_500), 12_500)

    def test_prefers_top_level_usd(self):
        amount, currency = _listing_price_from_info({"UAH": 557_500, "USD": 12_500, "EUR": 10_848})
        self.assertEqual((amount, currency), (12_500, "USD"))

    def test_falls_back_to_prices_array_strings(self):
        amount, currency = _listing_price_from_info(
            {
                "prices": [{"UAH": "557 500", "USD": "12 500", "EUR": "10 848"}],
            }
        )
        self.assertEqual((amount, currency), (12_500, "USD"))

    def test_info_to_listing_stores_usd(self):
        listing = info_to_listing(
            {
                "autoData": {"autoId": 1, "year": 2015, "raceInt": 207},
                "title": "Audi A4",
                "markName": "Audi",
                "modelName": "A4",
                "UAH": 557_500,
                "USD": 12_500,
                "EUR": 10_848,
                "linkToView": "/auto_audi_a4_1.html",
                "addDate": "2026-07-09 12:00:00",
            }
        )
        self.assertEqual(listing.price, 12_500)
        self.assertEqual(listing.currency, "USD")


if __name__ == "__main__":
    unittest.main()
