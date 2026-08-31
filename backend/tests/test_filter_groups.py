from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.parser.filter_groups import (
    filters_group_key,
    group_searches,
    merge_filters_for_fetch,
    similar_fetch_signature,
)


class FilterGroupTests(unittest.TestCase):
    def test_exact_grouping_unchanged(self):
        a = SearchFilters(brand="BMW", model="X5", year_from=2018, year_to=2020)
        b = SearchFilters(brand="BMW", model="X5", year_from=2018, year_to=2020)
        c = SearchFilters(brand="BMW", model="X5", year_from=2019, year_to=2022)
        groups = group_searches(
            [("s1", a.model_dump()), ("s2", b.model_dump()), ("s3", c.model_dump())],
            similar=False,
        )
        self.assertEqual(len(groups), 2)
        sizes = sorted(len(g.search_ids) for g in groups)
        self.assertEqual(sizes, [1, 2])

    def test_similar_grouping_same_brand_model(self):
        a = SearchFilters(brand="BMW", model="X5", year_from=2018, year_to=2020, price_to=20000)
        b = SearchFilters(brand="BMW", model="X5", year_from=2019, year_to=2022, price_from=15000)
        groups = group_searches(
            [("s1", a.model_dump()), ("s2", b.model_dump())],
            similar=True,
        )
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0].similar)
        self.assertEqual(set(groups[0].search_ids), {"s1", "s2"})
        self.assertEqual(groups[0].filters.year_from, 2018)
        self.assertEqual(groups[0].filters.year_to, 2022)
        self.assertEqual(groups[0].filters.price_from, 15000)
        self.assertEqual(groups[0].filters.price_to, 20000)

    def test_similar_does_not_merge_different_models(self):
        a = SearchFilters(brand="BMW", model="X5", year_from=2018)
        b = SearchFilters(brand="BMW", model="X3", year_from=2019)
        sig_a = similar_fetch_signature(a)
        sig_b = similar_fetch_signature(b)
        self.assertNotEqual(sig_a, sig_b)
        groups = group_searches(
            [("s1", a.model_dump()), ("s2", b.model_dump())],
            similar=True,
        )
        self.assertEqual(len(groups), 2)

    def test_no_brand_stays_exact(self):
        a = SearchFilters(price_from=10000, price_to=20000)
        b = SearchFilters(price_from=12000, price_to=18000)
        groups = group_searches(
            [("s1", a.model_dump()), ("s2", b.model_dump())],
            similar=True,
        )
        self.assertEqual(len(groups), 2)
        self.assertFalse(any(g.similar for g in groups))

    def test_different_regions_widen_to_none(self):
        merged = merge_filters_for_fetch(
            [
                SearchFilters(brand="BMW", region="м. Київ"),
                SearchFilters(brand="BMW", region="м. Львів"),
            ]
        )
        self.assertIsNone(merged.region)

    def test_different_currency_drops_price_from_fetch(self):
        merged = merge_filters_for_fetch(
            [
                SearchFilters(brand="BMW", price_to=20000, currency="USD"),
                SearchFilters(brand="BMW", price_to=800000, currency="UAH"),
            ]
        )
        self.assertIsNone(merged.price_from)
        self.assertIsNone(merged.price_to)

    def test_exact_keys_differ_for_similar_filters(self):
        a = SearchFilters(brand="BMW", model="X5", year_from=2018, year_to=2020)
        b = SearchFilters(brand="BMW", model="X5", year_from=2019, year_to=2022)
        self.assertNotEqual(filters_group_key(a), filters_group_key(b))

    def test_default_sources_include_car_market(self):
        merged = merge_filters_for_fetch(
            [
                SearchFilters(brand="BMW"),
                SearchFilters(brand="BMW", model="X5"),
            ]
        )
        self.assertIn("car_market", merged.sources or [])
        self.assertIn("lubeavto", merged.sources or [])
        self.assertIn("reono", merged.sources or [])
        self.assertIn("udrive", merged.sources or [])


if __name__ == "__main__":
    unittest.main()
