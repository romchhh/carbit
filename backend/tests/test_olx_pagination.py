"""OLX pagination helpers."""

from __future__ import annotations

import unittest

from app.services.olx.parser import has_next_page
from app.services.olx.service import _olx_collect_target, _olx_max_scan_pages


class OlxPaginationTests(unittest.TestCase):
    def test_collect_target_grows_with_page(self):
        t1 = _olx_collect_target(page=1, per_page=20, needs_post_filter=False)
        t2 = _olx_collect_target(page=2, per_page=20, needs_post_filter=False)
        self.assertLess(t1, t2)

    def test_post_filter_needs_more_pages(self):
        plain = _olx_max_scan_pages(collect_target=40, needs_post_filter=False, pool_size=False)
        filtered = _olx_max_scan_pages(collect_target=40, needs_post_filter=True, pool_size=False)
        self.assertGreaterEqual(filtered, plain)

    def test_pool_mode_allows_more_pages(self):
        pool = _olx_max_scan_pages(collect_target=500, needs_post_filter=True, pool_size=True)
        ui = _olx_max_scan_pages(collect_target=500, needs_post_filter=True, pool_size=False)
        self.assertGreaterEqual(pool, ui)

    def test_has_next_page_full_batch(self):
        self.assertTrue(
            has_next_page("", 1, page_listings_count=40, api_page_limit=40),
        )

    def test_has_next_page_from_json_total(self):
        html = 'window.__PRERENDERED_STATE__ = {"pagination":{"totalPages":5}}'
        self.assertTrue(has_next_page(html, 2, page_listings_count=10, api_page_limit=40))
        self.assertFalse(has_next_page(html, 5, page_listings_count=10, api_page_limit=40))


if __name__ == "__main__":
    unittest.main()
