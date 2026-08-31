"""Плутанина моделей у межах однієї марки.

Пошук «BMW 5 Series» повертав «BMW X5»: скорочення «<марка> <цифра>»
(потрібне для «Jaecoo 7» = J7) застосовувалось і там, де цифра насправді
позначає іншу модель марки.
"""

from __future__ import annotations

import datetime as dt
import unittest

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.brand_model_keywords import (
    bare_number_belongs_to_other_model,
    text_matches_brand_filter,
    text_matches_model_filter,
    text_names_other_model,
)
from app.services.telegram_channels.mapper import listing_out_matches_filters


def matches(title: str, brand: str, model: str) -> bool:
    return text_matches_brand_filter(title, brand) and text_matches_model_filter(
        title, model, brand=brand
    )


def make_listing(source: str, brand: str, model: str, title: str) -> ListingOut:
    now = dt.datetime.now(dt.timezone.utc)
    return ListingOut(
        id=f"{source}_1",
        source=source,
        title=title,
        brand=brand,
        model=model,
        year=2022,
        price=40000,
        currency="USD",
        mileage=30000,
        region="м. Київ",
        url="https://example.com/1",
        images=[],
        description=title,
        published_at=now,
        found_at=now,
        price_history=[],
        is_duplicate=False,
        fuel="Бензин",
        transmission="Автомат",
        seller_type="private",
    )


class LetterNumberModelTests(unittest.TestCase):
    def test_x_models_do_not_match_bare_series(self):
        for model, title in (
            ("X1", "BMW 1 Series 2020"),
            ("X3", "BMW 3 Series 2020"),
            ("X5", "BMW 5 Series GT 2020"),
            ("X6", "BMW 6 Series 2020"),
        ):
            with self.subTest(model=model):
                self.assertFalse(matches(title, "BMW", model))

    def test_i_models_do_not_match_bare_series(self):
        for model, title in (
            ("i3", "BMW 3 Series 2020"),
            ("i4", "BMW 4 Series 2020"),
            ("i5", "BMW 5 Series 2020"),
        ):
            with self.subTest(model=model):
                self.assertFalse(matches(title, "BMW", model))

    def test_series_filter_rejects_x_models(self):
        self.assertFalse(matches("BMW X5 M60I 2024", "BMW", "5 Series"))
        self.assertFalse(matches("BMW X3 xDrive20d", "BMW", "3 Series"))

    def test_series_filter_still_matches_own_trims(self):
        for title in ("BMW 520d 2018", "BMW 530i xDrive 2021", "BMW 5 Series 2019"):
            with self.subTest(title=title):
                self.assertTrue(matches(title, "BMW", "5 Series"))

    def test_x_filter_still_matches_own_model(self):
        self.assertTrue(matches("BMW X5 xDrive40i 2022", "BMW", "X5"))
        self.assertTrue(matches("BMW X3 2020", "BMW", "X3"))

    def test_other_series_numbers_do_not_match(self):
        """«5 Series» не має ловити «Series 3» чи «3 Series»."""
        for title in ("BMW Series 3 F30 330I Xdrive", "BMW 3 Series 2020", "BMW Series 7 G11"):
            with self.subTest(title=title):
                self.assertFalse(matches(title, "BMW", "5 Series"))

    def test_brand_number_shorthand_kept_where_unambiguous(self):
        """«Jaecoo 7» = J7: моделі, що починається з «7», у марки немає."""
        self.assertFalse(bare_number_belongs_to_other_model("Jaecoo", "7", "J7"))
        self.assertTrue(bare_number_belongs_to_other_model("BMW", "5", "X5"))

    def test_bare_number_model_rejects_cx_family(self):
        for title in ("Mazda CX-3 2020", "Mazda CX-5 2019", "Mazda CX-60 2023"):
            with self.subTest(title=title):
                self.assertFalse(matches(title, "Mazda", "3"))

    def test_bare_number_model_matches_itself(self):
        self.assertTrue(matches("Mazda 3 2020", "Mazda", "3"))
        self.assertTrue(matches("Mazda 6 2018", "Mazda", "6"))

    def test_cx_model_does_not_match_bare_number(self):
        self.assertFalse(matches("Mazda 5 2012", "Mazda", "CX-5"))
        self.assertFalse(matches("Mazda 3 2020", "Mazda", "CX-3"))


class NestedModelNameTests(unittest.TestCase):
    def test_q4_etron_is_not_plain_etron(self):
        self.assertFalse(matches("Audi e-tron 2020", "Audi", "Q4 e-tron"))

    def test_q4_etron_matches_itself(self):
        self.assertTrue(matches("Audi Q4 e-tron 2022", "Audi", "Q4 e-tron"))

    def test_plain_etron_still_works(self):
        self.assertTrue(matches("Audi e-tron 55 quattro", "Audi", "E-tron"))

    def test_etron_gt_is_not_plain_etron(self):
        self.assertFalse(matches("Audi e-tron GT 2023", "Audi", "E-tron"))
        self.assertTrue(matches("Audi e-tron GT 2023", "Audi", "E-tron GT"))

    def test_q8_etron_is_not_plain_q8(self):
        self.assertFalse(matches("Audi Q8 55 TFSI 2022", "Audi", "Q8 e-tron"))
        self.assertTrue(matches("Audi Q8 e-tron 2024", "Audi", "Q8 e-tron"))

    def test_q8_etron_is_not_plain_etron(self):
        self.assertFalse(matches("Audi e-tron 55 quattro", "Audi", "Q8 e-tron"))

    def test_plain_q8_does_not_match_q8_etron(self):
        self.assertFalse(matches("Audi Q8 e-tron 2024", "Audi", "Q8"))
        self.assertTrue(matches("Audi Q8 55 TFSI 2022", "Audi", "Q8"))


class SharedModelWordTests(unittest.TestCase):
    """Спільне слово кількох моделей марки саме по собі не ідентифікує модель."""

    def test_pace_family_is_not_interchangeable(self):
        self.assertFalse(matches("Jaguar E-Pace 2020", "Jaguar", "F-Pace"))
        self.assertFalse(matches("Jaguar F-Pace 2020", "Jaguar", "E-Pace"))

    def test_pace_models_match_themselves(self):
        self.assertTrue(matches("Jaguar F-Pace 2020", "Jaguar", "F-Pace"))
        self.assertTrue(matches("Jaguar E-Pace 30d 2021", "Jaguar", "E-Pace"))

    def test_picasso_family(self):
        self.assertFalse(matches("Citroen Xsara Picasso 2020", "Citroen", "C4 Picasso"))
        self.assertTrue(matches("Citroen C4 Picasso 2013", "Citroen", "C4 Picasso"))

    def test_cherokee_family(self):
        self.assertFalse(matches("Jeep Cherokee 2020", "Jeep", "Grand Cherokee"))
        self.assertTrue(matches("Jeep Grand Cherokee 2019", "Jeep", "Grand Cherokee"))
        self.assertTrue(matches("Jeep Cherokee 2018", "Jeep", "Cherokee"))

    def test_generation_number_is_the_same_car(self):
        """«718 Cayman» — це Cayman покоління 982, а не інша модель.

        Імперія Авто пише в заголовках просто «Porsche Cayman», тож
        відкидати їх при фільтрі «718 Cayman» не можна.
        """
        self.assertTrue(matches("Porsche Cayman 2017", "Porsche", "718 Cayman"))
        self.assertTrue(matches("Porsche Cayman S 2017", "Porsche", "718 Cayman"))
        self.assertTrue(matches("Porsche Boxster 2017", "Porsche", "718 Boxster"))
        self.assertTrue(matches("Porsche 718 Cayman GTS 2019", "Porsche", "718 Cayman"))

    def test_generation_number_does_not_mix_siblings(self):
        self.assertFalse(matches("Porsche Boxster 2017", "Porsche", "718 Cayman"))
        self.assertFalse(matches("Porsche 718 Boxster 2018", "Porsche", "718 Cayman"))
        self.assertFalse(matches("Porsche Cayman 2017", "Porsche", "Cayenne"))

    def test_unique_word_still_matches_short_form(self):
        """«Evoque» унікальний, тож коротка форма має працювати."""
        self.assertTrue(
            matches("Land Rover Evoque 2019", "Land Rover", "Range Rover Evoque")
        )

    def test_compound_body_still_matches(self):
        self.assertTrue(
            matches("Mercedes-Benz GLC 300 Coupe 2020", "Mercedes-Benz", "GLC Coupe")
        )
        self.assertTrue(matches("Mercedes-Benz GLC 220d 2020", "Mercedes-Benz", "GLC"))


class StampedModelGateTests(unittest.TestCase):
    """Поле «model» могло прийти з фільтра — заголовок головніший."""

    def test_stamped_model_does_not_beat_title(self):
        filters = SearchFilters.model_validate({"brand": "BMW", "model": "5 Series"})
        for source in ("auto_ria", "olx", "telegram"):
            with self.subTest(source=source):
                item = make_listing(source, "BMW", "5 Series", "BMW X5 M60I 2024")
                self.assertFalse(listing_out_matches_filters(item, filters))

    def test_matching_title_passes(self):
        filters = SearchFilters.model_validate({"brand": "BMW", "model": "5 Series"})
        item = make_listing("auto_ria", "BMW", "5 Series", "BMW 5 Series 2019")
        self.assertTrue(listing_out_matches_filters(item, filters))

    def test_model_only_in_structured_field_is_trusted(self):
        """Заголовок без моделі — структурному полю все ще віримо."""
        filters = SearchFilters.model_validate({"brand": "BMW", "model": "5 Series"})
        item = make_listing("olx", "BMW", "5 Series", "BMW 2019 в ідеальному стані")
        self.assertTrue(listing_out_matches_filters(item, filters))

    def test_text_names_other_model(self):
        self.assertTrue(text_names_other_model("BMW X5 M60I 2024", "BMW", "5 Series"))
        self.assertFalse(text_names_other_model("BMW 530i 2021", "BMW", "5 Series"))
        self.assertFalse(text_names_other_model("BMW 2019 добрий стан", "BMW", "5 Series"))


if __name__ == "__main__":
    unittest.main()
