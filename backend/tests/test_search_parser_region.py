"""Розпізнавання всіх областей у голосовому/AI-парсері."""

from __future__ import annotations

import unittest

from app.services.ai.search_parser import (
    _infer_region_from_transcript,
    _region_mentioned_in_transcript,
    _sanitize_region_from_transcript,
)
from app.services.search.region_voice import (
    CANONICAL_UA_REGIONS,
    _locative_adjective,
    infer_region_from_text,
    normalize_region_label,
    region_mentioned_in_text,
)

OBLASTS = [r for r in CANONICAL_UA_REGIONS if r.endswith(" область")]

DECLENSION_TEMPLATES = (
    "у {loc} області",
    "в {loc} області",
    "по {loc} області",
    "{nom} область",
    "{nom} обл",
    "{nom} області",
    "шукаю в {loc} області",
)


class RegionVoiceModuleTests(unittest.TestCase):
    def test_all_oblasts_locative_declension(self):
        for region in OBLASTS:
            nom = region.replace(" область", "")
            loc = _locative_adjective(nom)
            for tmpl in DECLENSION_TEMPLATES:
                text = tmpl.format(nom=nom.lower(), loc=loc.lower())
                with self.subTest(region=region, text=text):
                    self.assertTrue(
                        region_mentioned_in_text(text, region),
                        f"failed to match {region!r} in {text!r}",
                    )
                    self.assertEqual(infer_region_from_text(text), region)

    def test_all_oblasts_russian_style_oblast(self):
        for region in OBLASTS:
            adj = region.replace(" область", "")
            if not adj.endswith("ська"):
                continue
            ru_stem = adj[:-2] + "ск"
            text = f"в {ru_stem}ой области"
            with self.subTest(region=region, text=text):
                self.assertEqual(infer_region_from_text(text), region)

    def test_kyiv_city_vs_oblast(self):
        self.assertEqual(infer_region_from_text("bmw x5 у києві"), "м. Київ")
        self.assertEqual(
            infer_region_from_text("bmw x5 київська область"),
            "Київська область",
        )
        self.assertEqual(
            infer_region_from_text("bmw x5 у київській області"),
            "Київська область",
        )

    def test_major_city_aliases(self):
        samples = {
            "Львівська область": ("у львові", "lviv", "львов"),
            "Одеська область": ("в одесі", "odessa", "odesa"),
            "Харківська область": ("харків", "kharkiv"),
            "Дніпропетровська область": ("dnipro", "дніпро", "днепр"),
            "Волинська область": ("volyn", "у волинській області"),
        }
        for region, phrases in samples.items():
            for text in phrases:
                with self.subTest(region=region, text=text):
                    self.assertEqual(infer_region_from_text(text), region)

    def test_all_ukraine(self):
        for text in ("вся україна", "по всій україні", "по україні"):
            self.assertEqual(infer_region_from_text(text), "Вся Україна")

    def test_normalize_declined_label(self):
        self.assertEqual(
            normalize_region_label("волинській області"),
            "Волинська область",
        )
        self.assertEqual(
            normalize_region_label("львівській області"),
            "Львівська область",
        )


class SearchParserRegionIntegrationTests(unittest.TestCase):
    def test_volyn_oblast_declension(self):
        text = "Audi A5 2022 у волинській області"
        self.assertTrue(_region_mentioned_in_transcript(text, "Волинська область"))
        self.assertEqual(_infer_region_from_transcript(text), "Волинська область")

    def test_sanitize_keeps_valid_region(self):
        text = "Audi A5 у волинській області"
        filters = {"brand": "Audi", "model": "A5", "region": "Волинська область"}
        cleaned = _sanitize_region_from_transcript(text, filters)
        self.assertEqual(cleaned.get("region"), "Волинська область")

    def test_sanitize_drops_hallucinated_region(self):
        text = "Audi A5 2022"
        filters = {"brand": "Audi", "model": "A5", "region": "Волинська область"}
        cleaned = _sanitize_region_from_transcript(text, filters)
        self.assertNotIn("region", cleaned)

    def test_sanitize_infers_from_transcript(self):
        text = "Toyota Camry у тернопільській області"
        cleaned = _sanitize_region_from_transcript(text, {"brand": "Toyota"})
        self.assertEqual(cleaned.get("region"), "Тернопільська область")


if __name__ == "__main__":
    unittest.main()
