from __future__ import annotations

import unittest

from app.services.vin import extract_vin, is_valid_vin


SAMPLE_TEXT = """
Mercedes-Benz G63
2023
4.0 бензин
62 тис км
Повний привід

Офіційне авто, на гарантії. Автомобіль повністю обслужений, тільки після ТО.
Львів

269500$
0930057311

https://auto.ria.com/uk/auto_mercedes_benz_g_class_39895707.html

W1NWH5AB1SX014976
"""


class VinExtractTests(unittest.TestCase):
    def test_sample_mercedes_vin(self):
        self.assertEqual(extract_vin(SAMPLE_TEXT), "W1NWH5AB1SX014976")

    def test_labeled_vin(self):
        self.assertEqual(extract_vin("VIN: W1NWH5AB1SX014976 офіційне"), "W1NWH5AB1SX014976")
        self.assertEqual(extract_vin("ВІН код W1NWH5AB1SX014976"), "W1NWH5AB1SX014976")

    def test_ignores_ioq(self):
        self.assertIsNone(extract_vin("BADVINWITHIOQQQQ1"))  # has I/O/Q and wrong shape
        self.assertFalse(is_valid_vin("W1NWH5AB1SX01497I"))

    def test_does_not_fail_when_ioq_later_in_text(self):
        # Старий regex з (?!.*[IOQ]) ламався, якщо далі в тексті була літера I/O/Q.
        text = "W1NWH5AB1SX014976\nОфіційне авто IQ package"
        self.assertEqual(extract_vin(text), "W1NWH5AB1SX014976")

    def test_spaced_vin(self):
        self.assertEqual(extract_vin("W1N WH5AB1 SX014976"), "W1NWH5AB1SX014976")


if __name__ == "__main__":
    unittest.main()
