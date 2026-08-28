"""AUTO.RIA state_id ↔ наші назви областей (каталог /auto/states)."""

from __future__ import annotations

import unittest

from app.services.auto_ria.constants import REGION_TO_STATE_CITY, region_label_from_state_city

# Офіційні id з https://developers.ria.com/auto/states (2026).
AUTO_RIA_STATE_IDS: dict[str, int] = {
    "вінницька область": 1,
    "житомирська область": 2,
    "тернопільська область": 3,
    "хмельницька область": 4,
    "львівська область": 5,
    "чернігівська область": 6,
    "харківська область": 7,
    "сумська область": 8,
    "рівненська область": 9,
    "київська область": 10,
    "дніпропетровська область": 11,
    "одеська область": 12,
    "донецька область": 13,
    "запорізька область": 14,
    "івано-франківська область": 15,
    "кіровоградська область": 16,
    "волинська область": 18,
    "миколаївська область": 19,
    "полтавська область": 20,
    "закарпатська область": 22,
    "херсонська область": 23,
    "черкаська область": 24,
    "чернівецька область": 25,
}


class AutoRiaRegionMappingTests(unittest.TestCase):
    def test_oblast_state_ids_match_auto_ria_catalog(self):
        for region, expected_state in AUTO_RIA_STATE_IDS.items():
            mapped = REGION_TO_STATE_CITY.get(region)
            self.assertIsNotNone(mapped, region)
            state_id, city_id = mapped  # type: ignore[misc]
            self.assertEqual(city_id, 0, region)
            self.assertEqual(state_id, expected_state, region)

    def test_kyiv_city_uses_state_and_city(self):
        state_id, city_id = REGION_TO_STATE_CITY["м. київ"]
        self.assertEqual((state_id, city_id), (10, 10))

    def test_reverse_label_for_each_oblast(self):
        for region, state_id in AUTO_RIA_STATE_IDS.items():
            label = region_label_from_state_city(state_id)
            self.assertEqual(label, region, state_id)

    def test_luhansk_not_in_auto_ria_mapping(self):
        self.assertNotIn("луганська область", REGION_TO_STATE_CITY)


if __name__ == "__main__":
    unittest.main()
