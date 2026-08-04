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


if __name__ == "__main__":
    unittest.main()
