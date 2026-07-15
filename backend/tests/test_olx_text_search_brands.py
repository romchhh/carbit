"""OLX: марки без taxonomy path → text query."""

from __future__ import annotations

import unittest

from app.schemas.schemas import SearchFilters
from app.services.olx.brand_slugs import brand_uses_olx_text_search
from app.services.olx.mapper import filters_to_olx_params
from app.services.olx.parser import OlxListing, build_search_url, passes_olx_filters


class OlxTextSearchBrandTests(unittest.TestCase):
    def test_known_404_brands_use_text(self):
        for brand in (
            "Zeekr",
            "Haval",
            "Genesis",
            "Cupra",
            "Jaecoo",
            "Omoda",
            "XPeng",
            "NIO",
            "Li Auto",
            "Jetour",
            "Changan",
            "Dongfeng",
            "Skywell",
            "Voyah",
            "Lada",
            "BAIC",
            "GAC",
        ):
            self.assertTrue(brand_uses_olx_text_search(brand), brand)

    def test_path_brands_stay_on_taxonomy(self):
        for brand in ("Toyota", "BMW", "Geely", "JAC", "Chery", "Tesla", "MG", "BYD"):
            self.assertFalse(brand_uses_olx_text_search(brand), brand)

    def test_byd_url(self):
        params = filters_to_olx_params(
            SearchFilters(brand="BYD", model="Song Plus", currency="UAH")
        )
        self.assertEqual(params.text_query, "byd")
        url = build_search_url(params)
        self.assertIn("/q-byd/", url)
        self.assertNotIn("/legkovye-avtomobili/byd/", url)

    def test_text_search_uses_brand_only_url(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="USD")
        )
        self.assertEqual(params.text_query, "zeekr 001")
        self.assertEqual(params.model_label, "001")
        url = build_search_url(params)
        self.assertIn("/q-zeekr-001/", url)
        self.assertNotIn("/zeekr/001/", url)

    def test_build_url_hardens_stale_brand_path(self):
        """Навіть OlxSearchParams(brand=zeekr, model=001) → /q-zeekr-001/, не /zeekr/001/."""
        from app.services.olx.parser import OlxSearchParams

        broken = OlxSearchParams(
            brand="zeekr",
            model="001",
            city_query="kyiv",
            currency="USD",
            brand_label="Zeekr",
            model_label="001",
        )
        url = build_search_url(broken)
        self.assertIn("/q-zeekr-001/", url)
        self.assertNotIn("/zeekr/001/", url)
        self.assertNotIn("/q-kyiv/", url)

    def test_cyrillic_zeekr_uses_text(self):
        self.assertTrue(brand_uses_olx_text_search("Зікр"))
        params = filters_to_olx_params(
            SearchFilters(brand="Зікр", model="001", currency="UAH")
        )
        self.assertIn("/q-zeekr-001/", build_search_url(params))

    def test_haval_url(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Haval", model="Jolion", currency="USD")
        )
        self.assertEqual(params.text_query, "haval")
        self.assertIn("/q-haval/", build_search_url(params))

    def test_post_filter_keeps_model(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Zeekr", model="001", currency="USD")
        )
        keep = OlxListing(title="Zeekr 001 WE 2025", price="20500", currency="USD")
        drop = OlxListing(title="Zeekr 7x повний привід", price="45900", currency="USD")
        junk = OlxListing(title="Коврики EVA універсальні", price="500", currency="UAH")
        cyrillic = OlxListing(title="Зікр 001 You 2024", price="34000", currency="USD")
        self.assertTrue(passes_olx_filters(keep, params))
        self.assertFalse(passes_olx_filters(drop, params))
        self.assertFalse(passes_olx_filters(junk, params))
        self.assertTrue(passes_olx_filters(cyrillic, params))
    def test_jaecoo_j7_matches_jaecoo_7(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Jaecoo", model="J7", currency="USD")
        )
        keep = OlxListing(title="Jaecoo 7 Urban, 2025", price="25000", currency="USD")
        drop = OlxListing(title="Jaecoo 5 Premium", price="22000", currency="USD")
        self.assertTrue(passes_olx_filters(keep, params))
        self.assertFalse(passes_olx_filters(drop, params))

    def test_rejects_parts_and_scooters(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Haval", model="Jolion", currency="USD")
        )
        headlight = OlxListing(
            title="Фара для Haval Jolion",
            price="200",
            currency="USD",
            specs={"Тип запчастини": "Фара"},
        )
        self.assertFalse(passes_olx_filters(headlight, params))

        nio = filters_to_olx_params(SearchFilters(brand="NIO", currency="USD"))
        scooter = OlxListing(
            title="Електроскутер Fada Nio 2000W",
            price="500",
            currency="USD",
            raw_params={"category": {"id": 1941}},
        )
        self.assertFalse(passes_olx_filters(scooter, nio))

    def test_rejects_genesis_apartments(self):
        params = filters_to_olx_params(SearchFilters(brand="Genesis", currency="USD"))
        apt = OlxListing(
            title="Продам 1к квартиру ЖК GENESIS Шулявка",
            price="80000",
            currency="USD",
        )
        car = OlxListing(
            title="Genesis G70 Elite 3.3T AWD 2018",
            price="22000",
            currency="USD",
        )
        self.assertFalse(passes_olx_filters(apt, params))
        self.assertTrue(passes_olx_filters(car, params))

    def test_mercedes_class_uses_seriya_path(self):
        """OLX Mercedes класи — /e-seriya/, не /e-klass/ (404)."""
        params = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", model="E-Class", currency="USD")
        )
        self.assertIsNone(params.text_query)
        self.assertEqual(params.brand, "mercedes-benz")
        self.assertEqual(params.model, "e-seriya")
        url = build_search_url(params)
        self.assertIn("/mercedes-benz/e-seriya/", url)
        self.assertNotIn("e-klass", url)

        for model, slug in (
            ("C-Class", "c-seriya"),
            ("S-Class", "s-seriya"),
            ("A-Class", "a-seriya"),
            ("G-Class", "g-seriya"),
            ("CLS", "cls-seriya"),
            ("M-Class", "ml-seriya"),
        ):
            p = filters_to_olx_params(
                SearchFilters(brand="Mercedes-Benz", model=model, currency="UAH")
            )
            self.assertEqual(p.model, slug, model)
            self.assertIn(f"/mercedes-benz/{slug}/", build_search_url(p), model)

    def test_mercedes_brand_path(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", currency="USD")
        )
        url = build_search_url(params)
        self.assertIn("/mercedes-benz/", url)
        self.assertNotIn("/q-mercedes", url)

    def test_mercedes_title_aliases(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", model="E-Class", currency="USD")
        )
        # Path-based: text_query відсутній — title filter не застосовується.
        # Симулюємо fallback text search (після 404), коли фільтр по title увімкнений.
        params.text_query = "mercedes-benz"
        short = OlxListing(title="Mercedes E 220 CDI Avantgarde", price="12000", currency="USD")
        full = OlxListing(title="Mercedes-Benz E-Class 2018", price="18000", currency="USD")
        other = OlxListing(title="BMW 520d xDrive", price="15000", currency="USD")
        self.assertTrue(passes_olx_filters(short, params))
        self.assertTrue(passes_olx_filters(full, params))
        self.assertFalse(passes_olx_filters(other, params))

    def test_bmw_uses_serya_not_seriya(self):
        params = filters_to_olx_params(
            SearchFilters(brand="BMW", model="5 Series", currency="USD")
        )
        self.assertEqual(params.model, "5-serya")
        self.assertIn("/bmw/5-serya/", build_search_url(params))
        self.assertNotIn("seriya", build_search_url(params))

    def test_toyota_rav4_and_hilux_slugs(self):
        rav = filters_to_olx_params(SearchFilters(brand="Toyota", model="RAV4", currency="UAH"))
        self.assertEqual(rav.model, "rav-4")
        self.assertIn("/toyota/rav-4/", build_search_url(rav))

        hilux = filters_to_olx_params(SearchFilters(brand="Toyota", model="Hilux", currency="UAH"))
        self.assertEqual(hilux.model, "hilux-pick-up")

    def test_lexus_series_slugs(self):
        rx = filters_to_olx_params(SearchFilters(brand="Lexus", model="RX", currency="USD"))
        self.assertEqual(rx.model, "rx-serya")
        nx = filters_to_olx_params(SearchFilters(brand="Lexus", model="NX", currency="USD"))
        self.assertEqual(nx.model, "nx")
        self.assertIsNone(nx.text_query)

    def test_toyota_prado_forces_text(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Toyota", model="Land Cruiser Prado", currency="USD")
        )
        self.assertEqual(params.text_query, "toyota")
        self.assertIsNone(params.model)
        self.assertIn("/q-toyota/", build_search_url(params))

    def test_tesla_model_forces_text_brand_path_alone_ok(self):
        brand_only = filters_to_olx_params(SearchFilters(brand="Tesla", currency="USD"))
        self.assertIsNone(brand_only.text_query)
        self.assertEqual(brand_only.brand, "tesla")

        with_model = filters_to_olx_params(
            SearchFilters(brand="Tesla", model="Model 3", currency="USD")
        )
        self.assertEqual(with_model.text_query, "tesla")
        self.assertEqual(with_model.model_label, "Model 3")

    def test_byd_brand_path_model_text(self):
        brand_only = filters_to_olx_params(SearchFilters(brand="BYD", currency="UAH"))
        self.assertIsNone(brand_only.text_query)
        self.assertEqual(brand_only.brand, "byd")
        with_model = filters_to_olx_params(
            SearchFilters(brand="BYD", model="Song Plus", currency="UAH")
        )
        self.assertEqual(with_model.text_query, "byd")

    def test_mercedes_text_uses_mersedes_folk_query(self):
        """OLX народний пошук: /q-mersedes-glb/, не /q-mercedes-benz/."""
        params = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", model="GLB", currency="UAH")
        )
        self.assertEqual(params.text_query, "mersedes glb")
        url = build_search_url(params)
        self.assertIn("/q-mersedes-glb/", url)

    def test_mercedes_gla_keeps_taxonomy_path(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", model="GLA", currency="UAH")
        )
        self.assertIsNone(params.text_query)
        self.assertEqual(params.model, "gla")
        self.assertIn("/mercedes-benz/gla/", build_search_url(params))

    def test_mercedes_title_accepts_mersedes_spelling(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", model="GLB", currency="UAH")
        )
        hit = OlxListing(title="Mersedes GLB 200d 2021", price="25000", currency="USD")
        miss = OlxListing(title="BMW X1 sDrive18d", price="18000", currency="USD")
        self.assertTrue(passes_olx_filters(hit, params))
        self.assertFalse(passes_olx_filters(miss, params))

    def test_mercedes_text_query_variants(self):
        from app.services.olx.brand_slugs import build_olx_text_query_variants
        from app.services.olx.service import _build_search_param_variants

        queries = build_olx_text_query_variants("Mercedes-Benz", "GLA")
        self.assertIn("mersedes gla", queries)
        self.assertIn("mercedes gla", queries)
        self.assertTrue(any("мерседес" in q for q in queries))

        primary = filters_to_olx_params(
            SearchFilters(brand="Mercedes-Benz", model="GLA", currency="UAH")
        )
        variants = _build_search_param_variants(
            primary, SearchFilters(brand="Mercedes-Benz", model="GLA", currency="UAH")
        )
        # path primary + text folk queries
        self.assertGreaterEqual(len(variants), 2)
        self.assertIsNone(variants[0].text_query)
        self.assertTrue(any(v.text_query and "mersedes" in v.text_query for v in variants))
        urls = [build_search_url(v) for v in variants]
        self.assertTrue(any("/mercedes-benz/gla/" in u for u in urls))
        self.assertTrue(any("/q-mersedes-gla/" in u for u in urls))

    def test_catalog_covers_every_fe_model_path_or_text(self):
        """Кожна модель з FE або має confirmed path, або йде в text — без 404-roulette."""
        import re
        from pathlib import Path

        from app.services.olx.brand_slugs import (
            brand_model_forces_text_search,
            brand_uses_olx_text_search,
            resolve_olx_brand_slug,
            resolve_olx_model_slug,
        )
        from app.services.olx.olx_model_catalog import (
            OLX_EMPTY_MODEL_TAXONOMY_BRANDS,
            OLX_FE_MODEL_REMAP,
            OLX_KNOWN_MODEL_PATHS,
        )

        ts = Path(__file__).resolve().parents[2] / "frontend/src/lib/search-data/brands-models.ts"
        text = ts.read_text(encoding="utf-8")
        fe: dict[str, list[str]] = {}
        for m in re.finditer(
            r'(?:^|\n)\s*(?:\"([^\"]+)\"|([A-Za-z0-9]+))\s*:\s*\[([^\]]+)\]', text
        ):
            brand = m.group(1) or m.group(2)
            models = re.findall(r'\"([^\"]+)\"', m.group(3))
            if models:
                fe[brand] = models

        uncovered = []
        for brand, models in fe.items():
            if brand_uses_olx_text_search(brand):
                continue
            bslug = resolve_olx_brand_slug(brand)
            for model in models:
                forces = brand_model_forces_text_search(brand, model)
                params = filters_to_olx_params(
                    SearchFilters(brand=brand, model=model, currency="USD")
                )
                if forces:
                    self.assertTrue(params.text_query, f"{brand}/{model} should text")
                    continue
                self.assertIsNone(params.text_query, f"{brand}/{model}")
                slug = resolve_olx_model_slug(model, brand=brand)
                known = OLX_KNOWN_MODEL_PATHS.get(bslug, frozenset())
                if bslug in OLX_EMPTY_MODEL_TAXONOMY_BRANDS:
                    uncovered.append((brand, model, "empty-but-not-forced"))
                    continue
                if slug not in known and f"{bslug}|{model.lower()}" not in OLX_FE_MODEL_REMAP:
                    uncovered.append((brand, model, slug))
        self.assertEqual(uncovered, [], f"uncovered models: {uncovered[:20]}")


if __name__ == "__main__":
    unittest.main()
