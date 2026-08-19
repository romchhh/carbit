import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.core.timezone import now_kyiv
from app.services.auto_ria.mapper import sort_listings

UTC = ZoneInfo("UTC")


def _item(published_at: datetime, *, refreshed_at: datetime | None = None):
    return SimpleNamespace(
        published_at=published_at,
        refreshed_at=refreshed_at,
        price=100_000,
        year=2020,
        mileage=10_000,
    )


class SortListingsTests(unittest.TestCase):
    def test_newest_uses_kyiv_time_across_timezones(self):
        now = now_kyiv()
        items = [
            _item(now - timedelta(hours=5)),
            _item(datetime.now(UTC) - timedelta(minutes=10)),
            _item(now - timedelta(hours=1)),
        ]
        sorted_items = sort_listings(items, "newest")
        self.assertEqual(
            [item.published_at for item in sorted_items],
            sorted([item.published_at for item in items], key=lambda dt: dt, reverse=True),
        )

    def test_published_desc_is_newest_first(self):
        now = now_kyiv()
        older = _item(now - timedelta(days=1))
        newer = _item(now - timedelta(minutes=20))
        self.assertIs(sort_listings([older, newer], "published_desc")[0], newer)

    def test_published_asc_is_oldest_first(self):
        now = now_kyiv()
        older = _item(now - timedelta(days=3))
        newer = _item(now - timedelta(hours=2))
        self.assertIs(sort_listings([newer, older], "published_asc")[0], older)

    def test_newest_prefers_refreshed_at_when_present(self):
        now = now_kyiv()
        old_pub_fresh_refresh = _item(
            now - timedelta(weeks=4),
            refreshed_at=now - timedelta(hours=1),
        )
        recent_pub_no_refresh = _item(now - timedelta(hours=5))
        self.assertIs(
            sort_listings([recent_pub_no_refresh, old_pub_fresh_refresh], "newest")[0],
            old_pub_fresh_refresh,
        )


if __name__ == "__main__":
    unittest.main()
