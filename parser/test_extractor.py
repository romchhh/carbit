#!/usr/bin/env python3
"""Офлайн-тести екстрактора (без Telegram)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from parser.extractor import (
    extract_car_data,
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


if __name__ == "__main__":
    unittest.main()
