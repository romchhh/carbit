"""Джерела для категорії «Нові» — без OLX (таймаути / порожня видача)."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.schemas import PaginatedListings, SearchFilters
from app.services.search.multi_source import sources_for_filters


class NewCategorySourcesTests(unittest.TestCase):
    def test_new_excludes_olx_by_default(self):
        sources = sources_for_filters(SearchFilters(category="new"))
        self.assertNotIn("olx", sources)
        self.assertNotIn("car_market", sources)
        self.assertIn("auto_ria", sources)
        self.assertIn("udrive", sources)
        self.assertIn("imperiya", sources)

    def test_new_keeps_olx_when_only_source(self):
        sources = sources_for_filters(
            SearchFilters(category="new", sources=["OLX"])
        )
        self.assertEqual(sources, ["olx"])

    def test_used_excludes_udrive(self):
        sources = sources_for_filters(SearchFilters(category="used"))
        self.assertNotIn("udrive", sources)
        self.assertIn("olx", sources)

    def test_all_includes_everything(self):
        sources = sources_for_filters(SearchFilters(category="all"))
        self.assertIn("olx", sources)
        self.assertIn("car_market", sources)
        self.assertIn("udrive", sources)


class NewCategoryLivePoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_pool_skips_olx_for_new(self):
        from app.services.search.multi_source import build_live_search_pool

        with patch(
            "app.services.search.multi_source._search_olx_body",
            new_callable=AsyncMock,
        ) as olx_mock, patch(
            "app.services.auto_ria.service.collect_auto_ria_ids",
            new_callable=AsyncMock,
            return_value=([], 0),
        ), patch(
            "app.services.search.multi_source._fetch_source_pool",
            new_callable=AsyncMock,
            return_value=PaginatedListings(
                items=[], total=0, page=1, per_page=500, pages=0
            ),
        ):
            await build_live_search_pool(
                SearchFilters(category="new", brand="BMW"),
                sort_by="newest",
                max_ids=50,
                olx_enrich_details=False,
            )
        olx_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
