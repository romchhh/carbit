from __future__ import annotations

import unittest

from app.services.currency import (
    convert_price,
    format_display_price,
    format_price_uah,
    from_uah,
    resolve_display_currency,
    to_uah,
)


class CurrencyTests(unittest.TestCase):
    def test_usd_to_uah(self):
        self.assertEqual(to_uah(7350, "USD"), 330_750)
        self.assertEqual(to_uah(47500, "USD"), 2_137_500)

    def test_uah_stays_uah(self):
        self.assertEqual(to_uah(650_000, "UAH"), 650_000)

    def test_from_uah_roundtrip_usd(self):
        uah = to_uah(10_000, "USD")
        self.assertEqual(from_uah(uah, "USD"), 10_000)

    def test_same_currency_no_roundtrip_loss(self):
        # Раніше 16300$ → грн → $ давало 16131$ через чужий курс джерела.
        self.assertEqual(convert_price(16_300, "USD", "USD"), 16_300)
        self.assertEqual(convert_price(20_000, "USD", "USD"), 20_000)
        self.assertEqual(format_display_price(16_300, "USD", "USD"), "16 300 $")

    def test_format_price_eur_from_uah(self):
        self.assertEqual(format_price_uah(440_000, "EUR"), "10 000 €")

    def test_resolve_display_defaults_usd(self):
        self.assertEqual(resolve_display_currency(None), "USD")
        self.assertEqual(resolve_display_currency("eur"), "EUR")


if __name__ == "__main__":
    unittest.main()
