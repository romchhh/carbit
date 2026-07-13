"""Regression checks for live-search pool sizing / timeouts."""

from __future__ import annotations

import unittest

from app.services.search import multi_source, pool_cache


class LiveSearchPoolConfigTests(unittest.TestCase):
    def test_pool_caps_are_bounded(self):
        self.assertLessEqual(pool_cache.LIVE_POOL_SIZE, 100)
        self.assertLessEqual(multi_source.SOURCE_POOL_CAP, 100)
        self.assertEqual(pool_cache.LIVE_POOL_SIZE, multi_source.SOURCE_POOL_CAP)

    def test_auto_ria_pool_timeout_defined(self):
        self.assertGreater(multi_source.AUTO_RIA_POOL_TIMEOUT_SECONDS, 0)
        self.assertGreater(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 0)


if __name__ == "__main__":
    unittest.main()
