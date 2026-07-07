from __future__ import annotations

import unittest

from app.services.currency import infer_currency, to_uah


class CurrencyTests(unittest.TestCase):
    def test_usd_to_uah(self):
        self.assertEqual(to_uah(7350, "USD"), 301_350)
        self.assertEqual(to_uah(47500, "USD"), 1_947_500)

    def test_uah_stays_uah(self):
        self.assertEqual(to_uah(650_000, "UAH"), 650_000)

    def test_infer_usd_from_amount(self):
        self.assertEqual(infer_currency(7300, None, "Skoda Octavia 7300"), "USD")

    def test_infer_uah_from_text(self):
        self.assertEqual(infer_currency(650_000, None, "ціна 650 000 грн"), "UAH")


if __name__ == "__main__":
    unittest.main()
