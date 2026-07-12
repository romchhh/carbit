from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.auto_ria.constants import CURRENCY_UAH, CURRENCY_USD
from app.services.currency import filter_price_to_uah, resolve_filter_currency
from app.services.olx.mapper import filters_to_olx_params
from app.services.olx.parser import OlxSearchParams, build_search_url


class PriceCurrencyTests(unittest.TestCase):
    def test_auto_ria_currency_ids(self):
        self.assertEqual(CURRENCY_USD, 1)
        self.assertEqual(CURRENCY_UAH, 3)

    def test_resolve_filter_currency_defaults_uah_for_legacy(self):
        self.assertEqual(resolve_filter_currency(None), "UAH")
        self.assertEqual(resolve_filter_currency("USD"), "USD")
        self.assertEqual(resolve_filter_currency("UAH"), "UAH")

    def test_filter_price_to_uah_converts_usd(self):
        self.assertEqual(filter_price_to_uah(10_000, "USD"), 450_000)
        self.assertEqual(filter_price_to_uah(400_000, "UAH"), 400_000)
        self.assertIsNone(filter_price_to_uah(None, "USD"))

    def test_olx_url_uses_filter_currency(self):
        usd_url = build_search_url(OlxSearchParams(currency="USD"))
        uah_url = build_search_url(OlxSearchParams(currency="UAH"))
        self.assertIn("currency=USD", usd_url)
        self.assertIn("currency=UAH", uah_url)

    def test_olx_params_keep_usd_bounds_for_usd_filters(self):
        params = filters_to_olx_params(
            SearchFilters(price_from=10_000, price_to=22_000, currency="USD")
        )
        self.assertEqual(params.currency, "USD")
        self.assertEqual(params.price_from, 10_000)
        self.assertEqual(params.price_to, 22_000)

    def test_olx_params_convert_eur_bounds_to_uah(self):
        params = filters_to_olx_params(
            SearchFilters(price_from=10_000, price_to=22_000, currency="EUR")
        )
        self.assertEqual(params.currency, "UAH")
        self.assertEqual(params.price_from, 440_000)
        self.assertEqual(params.price_to, 968_000)


if __name__ == "__main__":
    unittest.main()
