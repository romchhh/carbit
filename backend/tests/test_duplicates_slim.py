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

    def test_dedupe_telegram_cross_channel_repost(self):
        from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

        ts = datetime(2026, 7, 20, tzinfo=KYIV_TZ)
        a = _item(
            id="telegram_channel_a_10",
            source="telegram",
            brand="BMW",
            model="X5",
            year=2019,
            price=25000,
            currency="USD",
            mileage=82000,
            url="https://t.me/channel_a/10",
            source_data={"channel": "channel_a", "message_id": 10},
            published_at=ts,
            found_at=ts,
            images=["a.jpg", "b.jpg"],
        )
        b = _item(
            id="telegram_channel_b_99",
            source="telegram",
            brand="BMW",
            model="X5",
            year=2019,
            price=25000,
            currency="USD",
            mileage=83000,  # той самий bucket 80000
            url="https://t.me/channel_b/99",
            source_data={"channel": "channel_b", "message_id": 99},
            published_at=ts,
            found_at=ts,
            images=["a.jpg"],
        )
        out = dedupe_telegram_posts_in_pool([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, "telegram_channel_a_10")

    def test_dedupe_telegram_different_price_kept(self):
        from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

        ts = datetime(2026, 7, 20, tzinfo=KYIV_TZ)
        a = _item(
            id="telegram_channel_a_10",
            source="telegram",
            brand="BMW",
            model="X5",
            year=2019,
            price=25000,
            title="BMW X5 2019 channel A",
            description="Інший опис авто A з унікальним текстом для відбитка",
            source_data={"channel": "channel_a", "message_id": 10},
            published_at=ts,
            found_at=ts,
        )
        b = _item(
            id="telegram_channel_b_99",
            source="telegram",
            brand="BMW",
            model="X5",
            year=2019,
            price=27000,
            title="BMW X5 2019 channel B",
            description="Зовсім інший опис авто B щоб текст не збігся випадково",
            source_data={"channel": "channel_b", "message_id": 99},
            published_at=ts,
            found_at=ts,
        )
        out = dedupe_telegram_posts_in_pool([a, b])
        self.assertEqual(len(out), 2)

    def test_dedupe_telegram_same_text_price_edit(self):
        """Репост того самого тексту з іншою ціною → одна картка."""
        from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

        ts = datetime(2026, 7, 31, tzinfo=KYIV_TZ)
        body = (
            "ПРОДАМ ФОЛЬЦВАГЕН ТУАРЕГ R LINE 2014 года, 3.6 бензин. "
            "Машина в отличном состоянии и не требует никакого ремонта. Все опции."
        )
        a = _item(
            id="telegram_avtobazar_group_100",
            source="telegram",
            brand="Volkswagen",
            model="Touareg",
            year=2014,
            price=17000,
            currency="UAH",
            title=body[:80],
            description=body,
            source_data={"channel": "avtobazar_group", "message_id": 100},
            published_at=ts,
            found_at=ts,
            images=["a.jpg"],
        )
        b = _item(
            id="telegram_avtobazar_group_101",
            source="telegram",
            brand="Volkswagen",
            model="Touareg",
            year=2014,
            price=16000,
            currency="UAH",
            title=body[:80],
            description=body,
            source_data={"channel": "avtobazar_group", "message_id": 101},
            published_at=ts,
            found_at=ts,
            images=["a.jpg", "b.jpg"],
        )
        out = dedupe_telegram_posts_in_pool([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, "telegram_avtobazar_group_101")

    def test_dedupe_telegram_same_channel_short_title_close_price(self):
        from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

        ts = datetime(2026, 7, 31, tzinfo=KYIV_TZ)
        a = _item(
            id="telegram_avtobazar_group_1",
            source="telegram",
            brand="Lada",
            model="",
            year=2014,
            price=18000,
            currency="UAH",
            title="Lada ння дзеркал 2014",
            description="",
            source_data={"channel": "avtobazar_group", "message_id": 1},
            published_at=ts,
            found_at=ts,
        )
        b = _item(
            id="telegram_avtobazar_group_2",
            source="telegram",
            brand="Lada",
            model="",
            year=2014,
            price=18500,
            currency="UAH",
            title="Lada ння дзеркал 2014",
            description="",
            source_data={"channel": "avtobazar_group", "message_id": 2},
            published_at=ts,
            found_at=ts,
        )
        out = dedupe_telegram_posts_in_pool([a, b])
        self.assertEqual(len(out), 1)

    def test_dedupe_telegram_same_title_far_price_kept(self):
        """Різні авто з однаковою короткою назвою, але різною ціною — не зливати."""
        from app.services.listings.duplicates import dedupe_telegram_posts_in_pool

        ts = datetime(2026, 7, 31, tzinfo=KYIV_TZ)
        a = _item(
            id="telegram_avtobazar_group_10",
            source="telegram",
            brand="Audi",
            model="SQ5",
            year=2018,
            price=22000,
            title="Audi SQ5 2018",
            description="",
            region="Україна",
            source_data={"channel": "avtobazar_group", "message_id": 10},
            published_at=ts,
            found_at=ts,
        )
        b = _item(
            id="telegram_avtobazar_group_11",
            source="telegram",
            brand="Audi",
            model="SQ5",
            year=2018,
            price=29000,
            title="Audi SQ5 2018",
            description="",
            region="Львів",
            source_data={"channel": "avtobazar_group", "message_id": 11},
            published_at=ts,
            found_at=ts,
        )
        out = dedupe_telegram_posts_in_pool([a, b])
        self.assertEqual(len(out), 2)

    def test_mark_pool_links_olx_and_telegram_by_vin(self):
        items = mark_duplicates_in_pool(
            [
                _item(
                    id="olx_audi",
                    source="olx",
                    brand="Audi",
                    model="Q5",
                    vin="WA1ANAFY6K2094900",
                    url="https://olx.example/audi-q5",
                ),
                _item(
                    id="telegram_audi",
                    source="telegram",
                    brand="Audi",
                    model="Q5 Quattro",
                    vin="WA1ANAFY6K2094900",
                    url="https://t.me/dealer/123",
                ),
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "olx")
        self.assertEqual(len(items[0].alternate_sources), 1)
        self.assertEqual(items[0].alternate_sources[0].source, "telegram")

    def test_mark_pool_prefers_auto_ria_and_links_olx(self):
        items = mark_duplicates_in_pool(
            [
                _item(
                    id="olx_audi",
                    source="olx",
                    brand="Audi",
                    model="Q5",
                    vin="WA1ANAFY6K2094900",
                    url="https://olx.example/audi-q5",
                ),
                _item(
                    id="auto_ria_audi",
                    source="auto_ria",
                    brand="Audi",
                    model="Q5",
                    vin="WA1ANAFY6K2094900",
                    url="https://auto.ria.example/audi-q5",
                ),
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "auto_ria")
        self.assertEqual(len(items[0].alternate_sources), 1)
        self.assertEqual(items[0].alternate_sources[0].source, "olx")

    def test_mark_pool_prefers_auto_ria_and_links_olx_legacy(self):
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


class MirrorLinkPersistenceTests(unittest.TestCase):
    """Повторне склеювання не має стирати вже знайдені дзеркала.

    У живому пошуку mark_duplicates_in_pool викликається двічі: спершу для
    пулу, потім у collapse_listings_with_db_mirrors. Другий прохід бачить уже
    згорнуту картку саму в групі — і раніше перезаписував alternate_sources
    порожнім списком, через що посилання на Імперію зникало з картки.
    """

    VIN = "WP0AB2A81JK278085"

    def _merged_pair(self) -> ListingOut:
        merged = mark_duplicates_in_pool(
            [
                _item(
                    id="auto_ria_38801428",
                    source="auto_ria",
                    vin=self.VIN,
                    url="https://auto.ria.com/auto_porsche_cayman_38801428.html",
                ),
                _item(
                    id="imperiya_51740",
                    source="imperiya",
                    vin=self.VIN,
                    url="https://imperiya-auto.com.ua/listing/porsche-cayman-51740",
                ),
            ]
        )
        self.assertEqual(len(merged), 1)
        return merged[0]

    def test_first_pass_keeps_imperiya_link(self):
        card = self._merged_pair()
        self.assertEqual(card.source, "auto_ria")
        self.assertEqual([a.source for a in card.alternate_sources], ["imperiya"])

    def test_second_pass_is_idempotent(self):
        card = self._merged_pair()
        again = mark_duplicates_in_pool([card])
        self.assertEqual(len(again), 1)
        self.assertEqual(
            [a.source for a in again[0].alternate_sources],
            ["imperiya"],
            "друге склеювання стерло дзеркало",
        )
        self.assertEqual(
            again[0].alternate_sources[0].url,
            "https://imperiya-auto.com.ua/listing/porsche-cayman-51740",
        )

    def test_repeated_passes_do_not_duplicate_links(self):
        card = self._merged_pair()
        for _ in range(3):
            card = mark_duplicates_in_pool([card])[0]
        self.assertEqual(len(card.alternate_sources), 1)

    def test_mirror_survives_merge_with_third_source(self):
        card = self._merged_pair()
        merged = mark_duplicates_in_pool(
            [
                card,
                _item(
                    id="olx_777",
                    source="olx",
                    vin=self.VIN,
                    url="https://olx.example/porsche-cayman",
                ),
            ]
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(
            sorted(a.source for a in merged[0].alternate_sources),
            ["imperiya", "olx"],
        )
