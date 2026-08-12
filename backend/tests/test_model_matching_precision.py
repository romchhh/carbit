"""Матчер brand/model не має «галюцинувати» на всьому FE-каталозі.

Повна версія аудиту — scripts/audit_model_matching.py. Тут компактний зріз
із фіксованим сідом, щоб регресії ловились у CI за секунди.
"""

from __future__ import annotations

import random
import unittest

from app.core.text import norm_text
from app.services.olx.brand_slugs import resolve_olx_brand_slug
from app.services.search.brand_model_keywords import (
    text_matches_brand_filter,
    text_matches_model_filter,
)
from app.services.search.fe_catalog import load_fe_brand_models

TITLE_TEMPLATES = (
    "{brand} {model} 2019",
    "Продам {brand} {model}, 2019 р.в., 120 000 км, Київ",
    "{brand} {model} 2019 — ідеальний стан, торг при огляді, 18 500$",
)


def _titles(brand: str, model: str) -> list[str]:
    return [tpl.format(brand=brand, model=model) for tpl in TITLE_TEMPLATES]


def _related(model_a: str, model_b: str) -> bool:
    a, b = norm_text(model_a), norm_text(model_b)
    if not a or not b or a == b:
        return True
    if a.startswith(b) or b.startswith(a):
        return True
    a_c = a.replace(" ", "").replace("-", "")
    b_c = b.replace(" ", "").replace("-", "")
    return a_c == b_c or a_c.startswith(b_c) or b_c.startswith(a_c)


def _same_family(brand_a: str, brand_b: str) -> bool:
    a, b = norm_text(brand_a), norm_text(brand_b)
    return bool(a) and bool(b) and (a in b or b in a)


class ModelMatchingPrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_fe_brand_models()
        cls.pairs = [
            (brand, model)
            for brand, models in sorted(cls.catalog.items())
            for model in models
        ]

    def test_catalog_loaded(self) -> None:
        self.assertGreater(len(self.pairs), 500, "FE-каталог не завантажився")

    def test_every_model_matches_its_own_listing(self) -> None:
        """Recall: жодна модель каталогу не має губити власне оголошення."""
        missed = [
            (brand, model, title)
            for brand, model in self.pairs
            for title in _titles(brand, model)
            if not text_matches_model_filter(title, model, brand=brand)
        ]
        self.assertEqual(missed, [], f"моделі не впізнали себе: {missed[:10]}")

    def test_no_cross_model_false_positives(self) -> None:
        """Precision: чуже авто не проходить гейт brand+model."""
        rng = random.Random(20240612)
        false_pos: list[tuple[str, str, str]] = []
        for brand, model in self.pairs:
            for other_brand, other_model in rng.sample(self.pairs, 8):
                if resolve_olx_brand_slug(other_brand) == resolve_olx_brand_slug(brand):
                    continue
                if _related(model, other_model) or _same_family(brand, other_brand):
                    continue
                if _same_family(other_brand, model.split()[0]):
                    continue
                title = f"{other_brand} {other_model} 2019"
                if not text_matches_brand_filter(title, brand, model=model):
                    continue
                if text_matches_model_filter(title, model, brand=brand):
                    false_pos.append((brand, model, title))
        self.assertEqual(false_pos, [], f"чужі авто пройшли: {false_pos[:10]}")

    def test_mileage_is_not_a_model_number(self) -> None:
        """«120 000 км» не має матчити числові моделі (Skoda 120, Mazda 323)."""
        noisy = [
            ("Skoda", "120", "Mitsubishi Pajero 2019, 120 000 км"),
            ("Skoda", "120", "Audi A4 2015, ціна 120 000 грн"),
            ("Skoda", "120", "Toyota Camry, пробіг 120 тис. км"),
            ("Mazda", "323", "Honda Civic 2010, 323 000 км"),
        ]
        for brand, model, title in noisy:
            with self.subTest(title=title):
                self.assertFalse(
                    text_matches_model_filter(title, model, brand=brand)
                )

        legit = [
            ("Skoda", "120", "Skoda 120 1985 р.в., 120 000 км"),
            ("Fiat", "500", "Fiat 500 2019, 120 000 км"),
            ("Mazda", "323", "Mazda 323 1998, 250 000 км"),
            ("Porsche", "911", "Porsche 911 Carrera 2018"),
        ]
        for brand, model, title in legit:
            with self.subTest(title=title):
                self.assertTrue(
                    text_matches_model_filter(title, model, brand=brand)
                )

    def test_submodel_does_not_inherit_other_brand_aliases(self) -> None:
        """Citroen C6 не має тягнути алієси Audi A6, Genesis G80 — BMW M3."""
        self.assertFalse(
            text_matches_model_filter("Audi A6 2019", "C6", brand="Citroen")
        )
        self.assertFalse(
            text_matches_model_filter("BMW M3 2019", "G80", brand="Genesis")
        )
        self.assertTrue(
            text_matches_model_filter("Citroen C6 2019", "C6", brand="Citroen")
        )
        self.assertTrue(
            text_matches_model_filter("Genesis G80 2021", "G80", brand="Genesis")
        )

    def test_shared_token_does_not_beat_named_brand(self) -> None:
        """Спільний токен не робить чуже авто нашою моделлю, коли в тексті
        прямо названо іншу марку («Toyota Land Cruiser» ≠ Chrysler PT Cruiser)."""
        cases = [
            ("Mercedes-Benz", "SLR McLaren", "McLaren 540C 2019"),
            ("Chrysler", "PT Cruiser", "Toyota Land Cruiser 2019"),
            ("Toyota", "FJ Cruiser", "Chrysler PT Cruiser 2005"),
            ("Chrysler", "Town & Country", "Lincoln Town Car 2019"),
            ("Chevrolet", "Spark", "Daewoo Matiz 2019"),
            ("Chevrolet", "Epica", "Daewoo Evanda 2019"),
            ("Volkswagen", "Transporter", "Dongfeng Forthing T5 EVO 2019"),
            ("Mitsubishi", "Lancer", "Dongfeng Forthing T5 EVO 2019"),
            ("BMW", "M3", "Genesis G80 2020"),
            ("Audi", "A6", "Citroen C5 Aircross 2019"),
            ("Toyota", "Land Cruiser", "Lexus LC 500 2021"),
            # Коротку марку «MG» не видно як марку, тож числовий трим
            # вимагає, щоб нашу марку назвали явно.
            ("BMW", "5 Series", "MG 550 2019"),
            ("BMW", "7 Series", "MG 750 2019"),
        ]
        for brand, model, title in cases:
            with self.subTest(model=model, title=title):
                self.assertFalse(
                    text_matches_model_filter(title, model, brand=brand)
                )

        legit = [
            ("Mercedes-Benz", "SLR McLaren", "Mercedes-Benz SLR McLaren 2006"),
            ("Chrysler", "PT Cruiser", "Chrysler PT Cruiser 2005"),
            ("Toyota", "Land Cruiser", "Toyota Land Cruiser 200 2015"),
            ("Volkswagen", "Transporter", "Volkswagen Transporter T5 2012"),
            ("BMW", "5 Series", "BMW 550i 2015"),
            ("Audi", "A6", "Audi A6 C5 1999"),
            # Суб-бренд: Huawei Aito — це Aito.
            ("Aito", "M5", "Huawei Aito M5 2023"),
        ]
        for brand, model, title in legit:
            with self.subTest(model=model, title=title):
                self.assertTrue(
                    text_matches_model_filter(title, model, brand=brand)
                )

    def test_two_letter_model_needs_brand_context(self) -> None:
        """Слово «is» — це Lexus IS лише поруч із маркою або з номером трима."""
        self.assertFalse(
            text_matches_model_filter(
                "Lexus RX 350. This is a great car, no rust", "IS", brand="Lexus"
            )
        )
        for title in ("Lexus IS 250 2010", "Продам Лексус IS 300h, 2015"):
            with self.subTest(title=title):
                self.assertTrue(
                    text_matches_model_filter(title, "IS", brand="Lexus")
                )

    def test_letter_class_coupe_respects_other_brand(self) -> None:
        """«Volvo S80 Coupe» — не Mercedes S-Class Coupe."""
        self.assertFalse(
            text_matches_model_filter(
                "Volvo S80 Coupe 2007", "S-Class Coupe", brand="Mercedes-Benz"
            )
        )
        for title in ("Mercedes-Benz S 500 Coupe 2018", "Mercedes S63 AMG Coupe"):
            with self.subTest(title=title):
                self.assertTrue(
                    text_matches_model_filter(
                        title, "S-Class Coupe", brand="Mercedes-Benz"
                    )
                )

    def test_model_glued_to_chassis_code(self) -> None:
        """«A4B6», «а4б7» — продавці пишуть модель і кузов без пробілу."""
        for title in ("Audi A4B6 2.5 QUATTRO", "Ауди а4б7 2:0 200ps"):
            with self.subTest(title=title):
                self.assertTrue(text_matches_model_filter(title, "A4", brand="Audi"))
        self.assertFalse(
            text_matches_model_filter("Audi A4B6 2.5 QUATTRO", "A6", brand="Audi")
        )

    def test_bmw_7_series_rejects_other_series(self) -> None:
        for title in ("BMW 5 Series 2011", "BMW 3 Series 2015", "BMW 5 серія 2011"):
            with self.subTest(title=title):
                self.assertFalse(
                    text_matches_model_filter(title, "7 Series", brand="BMW")
                )
        for title in ("BMW 740Li 2020", "BMW 750i 2019", "BMW 760i xDrive 2024"):
            with self.subTest(title=title):
                self.assertTrue(
                    text_matches_model_filter(title, "7 Series", brand="BMW")
                )

    def test_generic_trim_word_is_not_enough(self) -> None:
        """«Atlas Pro» не матчить «Tiggo 8 Pro», «Range Rover» — «Rover 618»."""
        cases = [
            ("Geely", "Atlas Pro", "Chery Tiggo 8 Pro 2019"),
            ("BYD", "Song Max", "Isuzu D-Max 2019"),
            ("BMW", "3 Series GT", "McLaren GT 2019"),
            ("Land Rover", "Range Rover", "Rover 618 1998"),
            ("Jaguar", "I-Pace", "Mini Paceman 2019"),
        ]
        for brand, model, title in cases:
            with self.subTest(model=model, title=title):
                self.assertFalse(
                    text_matches_model_filter(title, model, brand=brand)
                )


if __name__ == "__main__":
    unittest.main()
