"""Ціна не має братися з пробігу чи з довідкової ціни в дужках.

Реальний пост: «19 тис км … 95000$ (ріа 105000$)» давав ціну 19 000 $ —
шаблон «12 тис $» приймав «19 тис» ще й без валюти, бо валюта в ньому
необов'язкова.
"""

from __future__ import annotations

import unittest

from parser.extractor import _find_mileage, _find_price

BMW_X5_POST = """BMW X5 M60I
2024
4.4 бензин (530 к.с)
19 тис км
Повний привід

Автомобіль пригнаний цілим, був пошкоджений двигун. Два комплекти коліс.
Полтава

95000$ (ріа 105000$)
095 824 5374
@stasss13"""


class PriceVsMileageTests(unittest.TestCase):
    def test_mileage_in_thousands_is_not_a_price(self):
        amount, currency = _find_price(BMW_X5_POST.lower())
        self.assertEqual(amount, 95000.0)
        self.assertEqual(currency, "USD")

    def test_mileage_still_parsed(self):
        self.assertEqual(_find_mileage(BMW_X5_POST.lower()), 19000)

    def test_thousands_price_with_currency_still_works(self):
        for text, expected in (
            ("продам авто 12 тис $", 12000.0),
            ("ціна 15тис usd", 15000.0),
            ("отдам за 9 тыс$", 9000.0),
        ):
            with self.subTest(text=text):
                amount, _ = _find_price(text)
                self.assertEqual(amount, expected)

    def test_mileage_phrases_do_not_produce_price(self):
        for text in ("пробіг 19 тис км", "45 тис км, гарний стан", "19 тис.км"):
            with self.subTest(text=text):
                amount, _ = _find_price(text)
                self.assertNotEqual(amount, 19000.0)
                self.assertNotEqual(amount, 45000.0)


class ParentheticalPriceTests(unittest.TestCase):
    def test_price_outside_parens_wins(self):
        amount, _ = _find_price("95000$ (ріа 105000$)")
        self.assertEqual(amount, 95000.0)

    def test_reference_price_alone_is_used(self):
        """Якщо ціна лише в дужках — беремо її, іншої немає."""
        amount, _ = _find_price("автомобіль у Полтаві (ціна 32000$)")
        self.assertEqual(amount, 32000.0)


if __name__ == "__main__":
    unittest.main()
