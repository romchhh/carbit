"""Тести швидкого шляху Telegram keyword refresh."""

from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.search.brand_model_keywords import decode_telegram_keyword_job
from app.services.telegram_channels.keyword_refresh import (
    KEYWORD_WAIT_SECONDS,
    MAX_LIVE_TELEGRAM_SEARCH_QUERIES,
    TELEGRAM_KEYWORD_QUERY_PREFIX,
    TELEGRAM_SCAN_QUERY_PREFIX,
    build_telegram_keyword_queries,
)
from app.services.search import multi_source


class TelegramSearchSpeedTests(unittest.TestCase):
    def test_keyword_wait_is_short(self):
        self.assertLessEqual(KEYWORD_WAIT_SECONDS, 6.0)

    def test_pool_timeouts_are_bounded_for_live(self):
        self.assertLessEqual(multi_source.TELEGRAM_POOL_TIMEOUT_SECONDS, 30.0)
        self.assertLessEqual(multi_source.AUTO_RIA_POOL_TIMEOUT_SECONDS, 30.0)
        self.assertLessEqual(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 25.0)

    def test_live_queries_capped_and_scan_last(self):
        queries = build_telegram_keyword_queries(
            SearchFilters(brand="Mini", model="Countryman"),
            include_history_scan=True,
        )
        plain = [q for q in queries if not q.startswith(TELEGRAM_SCAN_QUERY_PREFIX)]
        scans = [q for q in queries if q.startswith(TELEGRAM_SCAN_QUERY_PREFIX)]
        self.assertLessEqual(len(plain), MAX_LIVE_TELEGRAM_SEARCH_QUERIES)
        self.assertEqual(len(scans), 1)
        self.assertTrue(queries[-1].startswith(TELEGRAM_SCAN_QUERY_PREFIX))
        self.assertIn("Countryman", plain[0])

    def test_mercedes_gls_telethon_queries_exact_latin_first(self):
        queries = build_telegram_keyword_queries(
            SearchFilters(brand="Mercedes-Benz", model="GLS"),
        )
        plain_q = []
        for job in queries:
            if not job.startswith(TELEGRAM_KEYWORD_QUERY_PREFIX):
                continue
            payload = decode_telegram_keyword_job(job)
            assert payload is not None
            plain_q.append(payload["q"])
        self.assertEqual(plain_q[0], "Mercedes-Benz GLS")
        self.assertIn("GLS", plain_q)
        self.assertNotIn("mersedes gls", [q.lower() for q in plain_q])

    def test_mercedes_g_class_telethon_includes_cyrillic_class(self):
        queries = build_telegram_keyword_queries(
            SearchFilters(brand="Mercedes-Benz", model="G-Class"),
        )
        plain_q = []
        for job in queries:
            if not job.startswith(TELEGRAM_KEYWORD_QUERY_PREFIX):
                continue
            payload = decode_telegram_keyword_job(job)
            assert payload is not None
            plain_q.append(payload["q"].lower())
        self.assertIn("g-класс", plain_q)
        self.assertTrue(any("mercedes-benz g-класс" in q for q in plain_q))


if __name__ == "__main__":
    unittest.main()
