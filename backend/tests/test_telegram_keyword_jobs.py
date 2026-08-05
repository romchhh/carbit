from __future__ import annotations

import unittest

from app.services.search.brand_model_keywords import (
    TELEGRAM_KEYWORD_QUERY_PREFIX,
    decode_telegram_keyword_job,
    encode_telegram_keyword_job,
    message_matches_search_filters,
)


class TelegramKeywordJobTests(unittest.TestCase):
    def test_encode_decode_keyword_job(self):
        raw = encode_telegram_keyword_job("Land Rover", "Discovery", "land rover discovery")
        self.assertTrue(raw.startswith(TELEGRAM_KEYWORD_QUERY_PREFIX))
        payload = decode_telegram_keyword_job(raw)
        assert payload is not None
        self.assertEqual(payload["brand"], "Land Rover")
        self.assertEqual(payload["model"], "Discovery")
        self.assertEqual(payload["q"], "land rover discovery")

    def test_message_matches_dealer_template(self):
        text = """📉 ЦІНУ ЗНИЖЕНО
🚗 Land Rover Discovery 2016
💰 14300 — власник щойно оновив ціну"""
        self.assertTrue(
            message_matches_search_filters(text, "Land Rover", "Discovery")
        )

    def test_message_rejects_wrong_model(self):
        text = "Mercedes-Benz E-Class 2016 15000$"
        self.assertFalse(
            message_matches_search_filters(text, "Land Rover", "Discovery")
        )

    def test_message_matches_bmw_xm_salon(self):
        text = """🔴 Марка: BMW | Модель: XM |
Ціна: 157000 $ | Пробіг: 13000 | Рік: 2024
XM Label Red 4.4 л V8
#BMW
📌 ІМПЕРІЯ АВТО"""
        self.assertTrue(message_matches_search_filters(text, "BMW", "XM"))

    def test_message_matches_mercedes_gls_salon(self):
        text = """🔴 Марка: Mercedes-Benz | Модель: GLS |
Ціна: 74900 $ | Пробіг: 110000 | Рік: 2021
#Mercedes-Benz
📌 ІМПЕРІЯ АВТО | Telegram • Сайt"""
        self.assertTrue(
            message_matches_search_filters(text, "Mercedes-Benz", "GLS")
        )


if __name__ == "__main__":
    unittest.main()
