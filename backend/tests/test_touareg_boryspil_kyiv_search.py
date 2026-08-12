"""Регресія: Touareg з Борисполя має проходити фільтр «м. Київ» і КПП «АКПП»."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.region_match import listing_region_matches_filter
from app.services.telegram_channels.mapper import listing_out_matches_filters


TOUAREG_POST = """
Volkswagen Touareg
Рік - 2014
3,0 дизель
АКПП
Повний привід
Пробіг 231 тис км
Vin: WVGEP9BP9ED013812
Місто Бориспіль
Ціна 17900₴
""".strip()


class TouaregBoryspilSearchTests(unittest.TestCase):
    def test_boryspil_matches_kyiv_oblast_filter(self) -> None:
        self.assertTrue(
            listing_region_matches_filter("Бориспіль", "Київська область"),
        )
        self.assertTrue(
            listing_region_matches_filter(
                f"Україна {TOUAREG_POST}",
                "Київська область",
            ),
        )

    def test_boryspil_matches_kyiv_city_filter(self) -> None:
        self.assertTrue(
            listing_region_matches_filter("Бориспіль", "м. Київ"),
        )
        self.assertTrue(
            listing_region_matches_filter(
                f"Україна {TOUAREG_POST}",
                "м. Київ",
            ),
        )

    def test_touareg_listing_passes_typical_filters(self) -> None:
        item = ListingOut(
            id="telegram:avtobazar_group:159845",
            source="telegram",
            title="Volkswagen Touareg 2014",
            brand="Volkswagen",
            model="Touareg",
            year=2014,
            price=17900,
            currency="USD",
            mileage=231000,
            fuel="Дизель",
            transmission="",
            region="Бориспіль",
            description=TOUAREG_POST,
            images=[],
            url="https://t.me/avtobazar_group/159845",
            seller_type="private",
            vin="WVGEP9BP9ED013812",
            vin_checked=None,
            vin_check_url=None,
            source_data={},
            price_history=[],
            is_duplicate=False,
            # Свіже: тест про марку/регіон/КПП, а не про вікно давності.
            published_at=datetime.now(timezone.utc) - timedelta(hours=1),
            found_at=datetime.now(timezone.utc),
        )
        filters = SearchFilters(
            brand="Volkswagen",
            model="Touareg",
            region="Київська область",
            transmission=["Автомат"],
            fuel=["Дизель"],
        )
        self.assertTrue(listing_out_matches_filters(item, filters))


if __name__ == "__main__":
    unittest.main()
