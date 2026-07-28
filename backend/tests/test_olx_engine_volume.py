"""Тести OLX engine volume з params/specs."""

from __future__ import annotations

import unittest

from app.services.olx.engine_volume import (
    extract_engine_volume_from_specs,
    extract_olx_listing_engine_volume,
    parse_olx_engine_spec_value,
)
from app.services.olx.mapper import olx_listing_to_listing_out
from app.services.olx.parser import OlxListing, OlxSearchParams, _listing_from_embedded, passes_olx_filters


class OlxEngineVolumeTests(unittest.TestCase):
    def test_parse_spec_litres(self):
        self.assertEqual(parse_olx_engine_spec_value("2.0 л"), 2.0)
        self.assertEqual(parse_olx_engine_spec_value("1998 см³"), 2.0)

    def test_specs_field_obem_dvyguna(self):
        specs = {"Обʼєм двигуна": "1.6 л"}
        self.assertEqual(extract_engine_volume_from_specs(specs), 1.6)

    def test_specs_apostrophe_variants(self):
        for key in ("Об'єм двигуна", "Обʼєм двигуна", "Объем двигуна"):
            specs = {key: "3.0 л"}
            self.assertEqual(extract_engine_volume_from_specs(specs), 3.0)

    def test_embedded_params_engine_capacity_key(self):
        raw = {
            "id": 777,
            "url": "/d/uk/obyavlenie/test-ID777.html",
            "title": "VW Passat",
            "params": [
                {"key": "engine_capacity", "name": "Обʼєм двигуна", "value": "2.0 л"},
            ],
        }
        listing = _listing_from_embedded(raw)
        assert listing is not None
        self.assertEqual(extract_olx_listing_engine_volume(listing), 2.0)
        self.assertIn("Обʼєм двигуна", listing.specs)

    def test_mapper_sets_engine_volume_l(self):
        listing = OlxListing(
            listing_id="123",
            title="Skoda Octavia",
            url="https://www.olx.ua/d/uk/obyavlenie/test-ID123.html",
            specs={"Обʼєм двигуна": "1.8 л"},
        )
        out = olx_listing_to_listing_out(listing)
        self.assertEqual(out.engine_volume_l, 1.8)

    def test_filter_by_engine_range(self):
        listing = OlxListing(
            listing_id="1",
            title="Test",
            url="https://www.olx.ua/d/uk/obyavlenie/test-ID1.html",
            specs={"Обʼєм двигуна": "3.0 л"},
        )
        in_range = OlxSearchParams(engine_from=2.5, engine_to=3.5)
        out_of_range = OlxSearchParams(engine_from=1.0, engine_to=1.5)
        self.assertTrue(passes_olx_filters(listing, in_range))
        self.assertFalse(passes_olx_filters(listing, out_of_range))


if __name__ == "__main__":
    unittest.main()
