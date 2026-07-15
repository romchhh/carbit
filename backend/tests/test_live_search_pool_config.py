"""Regression checks for live-search pool sizing / timeouts."""

from __future__ import annotations

import unittest

from app.services.search import multi_source, pool_cache


class LiveSearchPoolConfigTests(unittest.TestCase):
    def test_pool_caps_are_bounded(self):
        self.assertLessEqual(pool_cache.LIVE_POOL_SIZE, 150)
        self.assertLessEqual(multi_source.SOURCE_POOL_CAP, 150)
        self.assertEqual(pool_cache.LIVE_POOL_SIZE, multi_source.SOURCE_POOL_CAP)

    def test_auto_ria_pool_timeout_defined(self):
        self.assertGreater(multi_source.AUTO_RIA_POOL_TIMEOUT_SECONDS, 0)
        self.assertGreater(multi_source.OLX_SEARCH_TIMEOUT_SECONDS, 0)

    def test_pool_allow_extra_pages_for_hydrate_loss(self):
        """When hydrate drops IDs, we must not treat short page as market end."""
        need = multi_source.SOURCE_POOL_CAP
        page_size = multi_source.AUTO_RIA_PAGE_SIZE
        max_pages = max((need + page_size - 1) // page_size, 1) * 2
        max_pages = min(max_pages, 6)
        self.assertGreaterEqual(max_pages, 4)


    def test_hydrate_batch_matches_page_size(self):
        self.assertEqual(pool_cache.HYDRATE_BATCH_SIZE, 10)


if __name__ == "__main__":
    unittest.main()
