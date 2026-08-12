from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.parser.results import _result_matches_saved_model


def _listing(title: str, *, model: str = "", description: str = "") -> ListingOut:
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    return ListingOut(
        id="olx_1",
        source="olx",
        title=title,
        brand="BMW",
        model=model,
        description=description,
        price=11500,
        currency="USD",
        year=2011,
        mileage=272000,
        fuel="Бензин",
        transmission="Автомат",
        region="Одеса",
        url="https://olx.ua/1",
        images=[],
        seller_type="private",
        vin=None,
        vin_checked=None,
        vin_check_url=None,
        source_data={},
        price_history=[],
        is_duplicate=False,
        published_at=now,
        found_at=now,
    )


class SavedResultsModelGuardTests(unittest.TestCase):
    """Збережений моніторинг не має показувати те, що зматчив ще старий код."""

    def test_other_series_is_dropped(self) -> None:
        filters = SearchFilters(brand="BMW", model="7 Series")
        # model='7' підставляє мапер OLX із фільтра — сам себе підтвердити не може.
        item = _listing("BMW 5 Series 2011", model="7")
        self.assertFalse(_result_matches_saved_model(item, filters))

    def test_real_seven_series_is_kept(self) -> None:
        filters = SearchFilters(brand="BMW", model="7 Series")
        for title in ("BMW 740Li 2020", "BMW 7 Series E66", "Продам BMW 7 series 728"):
            with self.subTest(title=title):
                self.assertTrue(
                    _result_matches_saved_model(_listing(title, model="7"), filters)
                )

    def test_search_without_model_keeps_everything(self) -> None:
        filters = SearchFilters(brand="BMW")
        item = _listing("BMW 5 Series 2011", model="5 Series")
        self.assertTrue(_result_matches_saved_model(item, filters))

    def test_empty_title_is_not_dropped(self) -> None:
        filters = SearchFilters(brand="BMW", model="7 Series")
        self.assertTrue(_result_matches_saved_model(_listing(""), filters))


if __name__ == "__main__":
    unittest.main()
