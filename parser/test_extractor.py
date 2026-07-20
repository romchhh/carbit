#!/usr/bin/env python3
"""Офлайн-тести екстрактора (без Telegram)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from parser.extractor import (
    extract_car_data,
    is_car_search_request,
    is_promo_or_spam,
    is_valid_car_listing,
    normalize_listing_text,
)
from parser.models import CarListing


def _extract(text: str) -> CarListing:
    return extract_car_data(
        raw_text=text,
        channel="@test",
        message_id=1,
        group_message_ids=[1],
        source_link="https://t.me/test/1",
        posted_at=datetime.now(timezone.utc),
        photos=[],
    )


class ExtractorTests(unittest.TestCase):
    def test_normalize_markdown(self):
        raw = "**BMW X5** 2018 [деталі](https://t.me/x)"
        self.assertEqual(normalize_listing_text(raw), "BMW X5 2018 деталі")

    def test_bmw_cyrillic(self):
        listing = _extract("Продаю бмв x5 2018 рік, 3.0 дизель, 120 тис. км, 18500$")
        self.assertEqual(listing.brand, "BMW")
        self.assertEqual(listing.year, 2018)
        self.assertEqual(listing.price_amount, 18500)
        self.assertEqual(listing.price_currency, "USD")
        self.assertGreaterEqual(listing.confidence, 0.6)

    def test_mmr_price(self):
        listing = _extract("Jaguar F-PACE 2017\nMMR: $7,350\nПробіг: 98 тис. км")
        self.assertEqual(listing.brand, "Jaguar")
        self.assertEqual(listing.price_amount, 7350)
        self.assertEqual(listing.price_currency, "USD")

    def test_usd_without_symbol_import_channel(self):
        listing = _extract("Skoda Octavia 2012 рік, ціна 7300, пробіг 118 тис км")
        self.assertEqual(listing.price_currency, "USD")

    def test_uah_price(self):
        listing = _extract("Audi A4 2016, ціна 650 000 грн, Київ")
        self.assertEqual(listing.brand, "Audi")
        self.assertEqual(listing.price_amount, 650000)
        self.assertEqual(listing.price_currency, "UAH")

    def test_mercedes_nbsp_price(self):
        listing = _extract("Mercedes-Benz GLC-Class Coupe 2021\n💰 47\u00a0500\u00a0$\n📏 60 тис. км")
        self.assertEqual(listing.year, 2021)
        self.assertEqual(listing.price_amount, 47500)
        self.assertEqual(listing.price_currency, "USD")

    def test_man_not_in_roman(self):
        listing = _extract("Roman продам авто без посередників, 2015 рік, 12000$")
        self.assertNotEqual(listing.brand, "MAN")

    def test_spam_webinar(self):
        text = "Вебінар 15 липня: як продавати авто в 2026 році. Підпишись на канал!"
        self.assertTrue(is_promo_or_spam(text.lower()))
        listing = _extract(text)
        self.assertFalse(is_valid_car_listing(listing))

    def test_valid_listing(self):
        listing = _extract("Mercedes E220 2019, 25000$, не бита, Одеса")
        self.assertTrue(is_valid_car_listing(listing))

    def test_empty_photo_only(self):
        listing = _extract("")
        self.assertFalse(is_valid_car_listing(listing))

    def test_buyer_search_request_bmw_list(self):
        text = """#Пошук авто🕵️

BMW от 2020 г.в.:
X5M F95 - до 65$
X5M50i - до 55$
X5 G05 (LCI) 3.0 - 60$
X5 G05 (дорест) 3.0 в М-пак - 40$
M8 F92/93 - до 65$
M5 F90 (рест) - до 65$
X6 также рассмотрю

✍️ @nik_6699"""
        self.assertTrue(is_car_search_request(text))
        listing = _extract(text)
        self.assertFalse(is_valid_car_listing(listing))

    def test_sale_listing_not_search_request(self):
        text = "Продаю BMW X5 2021, пробіг 45 тис, 52000$"
        self.assertFalse(is_car_search_request(text))
        listing = _extract(text)
        self.assertTrue(is_valid_car_listing(listing))

    def test_hashtags_stripped(self):
        listing = _extract("#авто #продам Toyota Camry 2017, 14500$")
        self.assertEqual(listing.brand, "Toyota")
        self.assertEqual(listing.year, 2017)

    def test_hashtags_keep_brand_and_vin(self):
        raw = """#Zeekr #001 Facelift

Zeekr 001 Facelift
2024 рік
13к пробіг
електро
Повний привід

📍 м. Київ

#L6T79ZCE4RP134189

💰47.000$💰45.000$
✍️ @KT1255E
"""
        listing = _extract(raw)
        self.assertEqual(listing.brand, "Zeekr")
        self.assertIn("001", listing.model or "")
        self.assertEqual(listing.year, 2024)
        self.assertEqual(listing.mileage_km, 13000)
        self.assertEqual(listing.fuel_type, "electric")
        self.assertEqual(listing.drive_type, "awd")
        self.assertEqual(listing.location_city, "Київ")
        self.assertEqual(listing.price_amount, 45000)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.condition_flags.get("vin"), "L6T79ZCE4RP134189")
        self.assertEqual(listing.contact_username, "KT1255E")
        self.assertNotEqual(listing.condition_flags.get("vin"), "FACELFTZEEKR001FA")

    def test_mileage_short_k(self):
        listing = _extract("BMW X5 2019\n85к пробіг\n22000$")
        self.assertEqual(listing.mileage_km, 85000)

    def test_year_with_cyrillic_g_suffix(self):
        listing = _extract(
            "MAZDA MX-30 2021г. Электро 35,5 kWt 45 тыс.км. Автомат. "
            "Без ДТП, все в оригинале. Запас хода 220 км. 14900$. 067-7960229"
        )
        self.assertEqual(listing.brand, "Mazda")
        self.assertEqual(listing.year, 2021)
        self.assertEqual(listing.model, "MX-30")
        self.assertEqual(listing.price_amount, 14900)
        self.assertEqual(listing.mileage_km, 45000)

    def test_year_rik_suffix(self):
        listing = _extract("Toyota Camry 2019 рік, 14500$")
        self.assertEqual(listing.year, 2019)
        self.assertEqual(listing.model, "Camry")

    def test_mileage_label(self):
        listing = _extract("Volkswagen Passat 2015\nПробіг: 145 тис. км\nЦіна: 9800$")
        self.assertEqual(listing.brand, "Volkswagen")
        self.assertEqual(listing.mileage_km, 145000)
        self.assertEqual(listing.price_amount, 9800)

    def test_full_km_mileage(self):
        listing = _extract("Ford Focus 2014, пробіг 118000 км, 7500$")
        self.assertEqual(listing.mileage_km, 118000)

    def test_phone_not_price(self):
        listing = _extract("Продам авто, тел 0671234567, 2016 рік")
        self.assertNotEqual(listing.price_amount, 671234567)

    def test_vin_flag(self):
        listing = _extract("BMW 320 2016, VIN WBA8E9G50JNU12345, 12000$")
        self.assertEqual(listing.condition_flags.get("vin"), "WBA8E9G50JNU12345")

    def test_vin_from_plain_line(self):
        text = """
Mercedes-Benz G63 2023
269500$
W1NWH5AB1SX014976
"""
        listing = _extract(text)
        self.assertEqual(listing.condition_flags.get("vin"), "W1NWH5AB1SX014976")

    def test_vin_not_blocked_by_later_letter_i(self):
        listing = _extract("Toyota Camry 2018 9000$\nWBA8E9G50JNU12345\nOfficial import")
        self.assertEqual(listing.condition_flags.get("vin"), "WBA8E9G50JNU12345")


if __name__ == "__main__":
    unittest.main()
