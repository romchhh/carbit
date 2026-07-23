"""Тести крос-джерельних дублікатів і slim list payload."""

from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut
from app.services.listings.duplicates import listings_look_same, mark_duplicates_in_pool
from app.services.listings.sanitize import slim_listing_for_list, slim_source_data_for_list


def _item(**kwargs) -> ListingOut:
    base = dict(
        id="auto_ria_1",
        source="auto_ria",
        title="BMW 320",
        brand="BMW",
        model="320",
        year=2019,
        price=15000,
        currency="USD",
        mileage=80000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://example.com",
        seller_type="private",
        vin=None,
        source_data={"USD": 15000, "_fotos": [{"id": 1}], "noise": "x"},
        price_history=[],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(kwargs)
    return ListingOut(**base)


class DuplicatesTests(unittest.TestCase):
    def test_same_vin(self):
        a = _item(id="a", vin="WBA8E9C50HK123456")
        b = _item(id="b", source="olx", vin="WBA8E9C50HK123456", mileage=90000)
        self.assertTrue(listings_look_same(a, b))

    def test_mark_pool_two_olx_same_vin(self):
        vin = "WF0GXXGBBG7Y21048"
        items = mark_duplicates_in_pool(
            [
                _item(
                    id="olx_a",
                    source="olx",
                    vin=vin,
                    url="https://olx.example/a",
                    region="Вінницька область",
                ),
                _item(
                    id="olx_b",
                    source="olx",
                    vin=vin,
                    url="https://olx.example/b",
                    region="Вінниця",
                    mileage=216000,
                ),
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "olx")
        self.assertEqual(len(items[0].alternate_sources), 1)
        self.assertEqual(items[0].alternate_sources[0].source, "olx")

    def test_brand_model_year_mileage_not_duplicate_without_vin(self):
        a = _item(id="a", mileage=80000)
        b = _item(id="b", source="olx", mileage=82000)
        self.assertFalse(listings_look_same(a, b))

    def test_same_price_repost_not_duplicate_without_vin(self):
        a = _item(id="a", source="olx", mileage=0, price=7699, currency="USD")
        b = _item(id="b", source="olx", mileage=216000, price=7699, currency="USD")
        self.assertFalse(listings_look_same(a, b))

    def test_same_price_different_mileage_not_duplicate(self):
        a = _item(
            id="a",
            source="olx",
            brand="Zeekr",
            model="001",
            year=2025,
            mileage=20000,
            price=19800,
        )
        b = _item(
            id="b",
            source="olx",
            brand="Zeekr",
            model="001",
            year=2025,
            mileage=90000,
            price=19800,
        )
        self.assertFalse(listings_look_same(a, b))

    def test_prefer_id_keeps_url_on_detail(self):
        vin = "WBA8E9C50HK123456"
        items = mark_duplicates_in_pool(
            [
                _item(
                    id="olx_b",
                    source="olx",
                    brand="Zeekr",
                    model="001",
                    year=2025,
                    mileage=20000,
                    price=19800,
                    url="https://olx.example/b",
                    vin=vin,
                ),
                _item(
                    id="olx_a",
                    source="olx",
                    brand="Zeekr",
                    model="001",
                    year=2025,
                    mileage=21000,
                    price=19800,
                    url="https://olx.example/a",
                    vin=vin,
                ),
            ],
            prefer_id="olx_b",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "olx_b")
        self.assertEqual(items[0].url, "https://olx.example/b")
        self.assertEqual(len(items[0].alternate_sources), 1)
        self.assertEqual(items[0].alternate_sources[0].url, "https://olx.example/a")

    def test_dedupe_same_telegram_post_different_listing_ids(self):
        from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

        ts = datetime(2026, 7, 20, tzinfo=KYIV_TZ)
        a = _item(
            id="telegram_testchannel_100",
            source="telegram",
            url="https://t.me/testchannel/100",
            source_data={"channel": "testchannel", "message_id": 100, "photo_message_ids": [100, 101]},
            published_at=ts,
            found_at=ts,
        )
        b = _item(
            id="telegram_TestChannel_100",
            source="telegram",
            url="https://t.me/testchannel/100",
            source_data={"channel": "TestChannel", "message_id": 100, "photo_message_ids": [100, 101]},
            published_at=ts,
            found_at=ts,
        )
        out = dedupe_telegram_posts_in_pool([a, b])
        self.assertEqual(len(out), 1)

    def test_mark_pool_prefers_auto_ria_and_links_olx(self):
        items = mark_duplicates_in_pool(
            [
                _item(
                    id="b",
                    source="olx",
                    vin="WBA8E9C50HK123456",
                    url="https://olx.example/1",
                ),
                _item(
                    id="a",
                    vin="WBA8E9C50HK123456",
                    url="https://auto.ria.example/1",
                ),
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "a")
        self.assertEqual(items[0].source, "auto_ria")
        self.assertFalse(items[0].is_duplicate)
        self.assertIsNone(items[0].duplicate_of)
        self.assertEqual(len(items[0].alternate_sources), 1)
        self.assertEqual(items[0].alternate_sources[0].source, "olx")
    def test_mark_pool_propagates_is_new(self):
        vin = "WBA8E9C50HK123457"
        items = mark_duplicates_in_pool(
            [
                _item(id="a", is_new=False, vin=vin),
                _item(
                    id="b",
                    source="olx",
                    mileage=82000,
                    url="https://olx.example/1",
                    is_new=True,
                    vin=vin,
                ),
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].is_new)
    def test_drops_heavy_keys(self):
        slim = slim_source_data_for_list({"USD": 1, "_fotos": [], "noise": "no"})
        self.assertEqual(slim, {"USD": 1})

    def test_slim_listing(self):
        item = slim_listing_for_list(_item())
        self.assertNotIn("_fotos", item.source_data or {})
        self.assertNotIn("noise", item.source_data or {})
        self.assertIn("USD", item.source_data or {})


if __name__ == "__main__":
    unittest.main()
