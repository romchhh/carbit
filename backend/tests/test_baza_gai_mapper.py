"""Тести мапера Бази ДАІ (без реального API-ключа)."""

from __future__ import annotations

import unittest

from app.services.baza_gai.mapper import map_vin_payload


SAMPLE = {
    "digits": "KA0007XB",
    "vin": "WBA7J21060G057838",
    "region": {
        "name": "г. Киев",
        "name_ua": "м. Київ",
        "slug": "kyiv",
        "old_code": "AA",
        "new_code": "KA",
    },
    "vendor": "BMW",
    "model": "M760LI",
    "model_year": 2021,
    "photo_url": "https://baza-gai.com.ua/catalog-images/bmw/7er/image.jpg",
    "is_stolen": False,
    "stolen_details": None,
    "operations": [
        {
            "is_last": True,
            "registered_at": "03.04.2021",
            "model_year": 2021,
            "vendor": "BMW",
            "model": "M760LI",
            "operation": {
                "ru": "Первичная регистрация",
                "ua": "Первинна реєстрація нового тз",
            },
            "department": "ТСЦ 8047",
            "color": {"slug": "gray", "ru": "Серый", "ua": "Сірий"},
            "address": "м.Київ, Деснянський",
            "operation_group": {"id": 1, "ru": "Первичная регистрация", "ua": "Первинна реєстрація"},
        }
    ],
}


class BazaGaiMapperTests(unittest.TestCase):
    def test_maps_vin_payload(self):
        out = map_vin_payload(SAMPLE, vin="WBA7J21060G057838")
        self.assertEqual(out.vin, "WBA7J21060G057838")
        self.assertEqual(out.digits, "KA0007XB")
        self.assertEqual(out.vendor, "BMW")
        self.assertEqual(out.model, "M760LI")
        self.assertEqual(out.model_year, 2021)
        self.assertEqual(out.region, "м. Київ")
        self.assertFalse(out.is_stolen)
        self.assertEqual(len(out.operations), 1)
        self.assertEqual(out.operations[0].operation, "Первинна реєстрація нового тз")
        self.assertEqual(out.operations[0].color, "Сірий")
        self.assertTrue(out.source_url.endswith("/vin/WBA7J21060G057838"))

    def test_maps_stolen_details(self):
        raw = {
            **SAMPLE,
            "is_stolen": True,
            "stolen_details": [
                {
                    "theft_at": "15.01.2022",
                    "vendor_title": "MERCEDES-BENZ - ATEGO",
                    "color": {"title": {"ua": "БЕЖЕВИЙ", "ru": "Бежевый"}},
                    "car_type": "Вантажний автотранспорт",
                    "chassis_number": "WDB9XXXX",
                    "department_title": "ГУНП",
                }
            ],
        }
        out = map_vin_payload(raw, vin="WBA7J21060G057838")
        self.assertTrue(out.is_stolen)
        self.assertEqual(len(out.stolen_details), 1)
        self.assertEqual(out.stolen_details[0].color, "БЕЖЕВИЙ")


if __name__ == "__main__":
    unittest.main()
