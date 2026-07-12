from __future__ import annotations

import unittest

from app.services.currency import (
    format_price_uah,
    from_uah,
    infer_currency,
    resolve_display_currency,
    to_uah,
)


class CurrencyTests(unittest.TestCase):
    def test_usd_to_uah(self):
        self.assertEqual(to_uah(7350, "USD"), 330_750)
        self.assertEqual(to_uah(47500, "USD"), 2_137_500)

    def test_uah_stays_uah(self):
        self.assertEqual(to_uah(650_000, "UAH"), 650_000)

    def test_infer_usd_from_amount(self):
        self.assertEqual(infer_currency(7300, None, "Skoda Octavia 7300"), "USD")

    def test_infer_uah_from_text(self):
        self.assertEqual(infer_currency(650_000, None, "ціна 650 000 грн"), "UAH")

    def test_from_uah_roundtrip_usd(self):
        uah = to_uah(10_000, "USD")
        self.assertEqual(from_uah(uah, "USD"), 10_000)

    def test_format_price_eur(self):
        # 440_000 грн ≈ 10_000 €
        self.assertEqual(format_price_uah(440_000, "EUR"), "10 000 €")

    def test_resolve_display(self):
        self.assertEqual(resolve_display_currency("eur"), "EUR")
        self.assertEqual(resolve_display_currency(None), "UAH")


if __name__ == "__main__":
    unittest.main()
