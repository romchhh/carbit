from datetime import datetime, timedelta, timezone

from app.core.timezone import KYIV_TZ, now_kyiv
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.search.multi_source import _filter_listings_by_published_filters


def _listing(listing_id: str, published_at: datetime) -> ListingOut:
    return ListingOut(
        id=listing_id,
        source="olx",
        title="Test",
        brand="Toyota",
        model="Camry",
        year=2020,
        price=10000,
        currency="USD",
        mileage=100000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description="",
        images=[],
        url="https://example.com",
        seller_type="private",
        vin=None,
        engine_volume_l=None,
        source_data={},
        price_history=[],
        is_duplicate=False,
        published_at=published_at,
        found_at=published_at,
    )


def test_filter_listings_by_custom_published_range():
    now = datetime(2026, 8, 19, 12, 0, tzinfo=KYIV_TZ)
    items = [
        _listing("old", now - timedelta(days=10)),
        _listing("mid", now - timedelta(days=2)),
        _listing("new", now - timedelta(hours=2)),
    ]
    filters = SearchFilters(
        published_from=now - timedelta(days=3),
        published_to=now,
    )
    result = _filter_listings_by_published_filters(items, filters)
    assert [item.id for item in result] == ["mid", "new"]


def test_filter_listings_by_published_within_days():
    now = now_kyiv()
    items = [
        _listing("old", now - timedelta(days=10)),
        _listing("fresh", now - timedelta(days=1)),
    ]
    filters = SearchFilters(published_within_days=3)
    result = _filter_listings_by_published_filters(items, filters)
    assert [item.id for item in result] == ["fresh"]


def test_filter_listings_by_published_older_than_days():
    now = now_kyiv()
    items = [
        _listing("very_old", now - timedelta(days=45)),
        _listing("old_enough", now - timedelta(days=16)),
        _listing("fresh", now - timedelta(days=5)),
    ]
    filters = SearchFilters(published_older_than_days=15)
    result = _filter_listings_by_published_filters(items, filters)
    assert [item.id for item in result] == ["very_old", "old_enough"]


def test_build_live_search_pool_applies_published_older_than_days():
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.services.search.multi_source import build_live_search_pool

    now = now_kyiv()
    fresh = _listing("fresh", now - timedelta(hours=1))
    old = _listing("old", now - timedelta(days=20))

    async def run():
        with patch(
            "app.services.auto_ria.service.collect_auto_ria_ids",
            new_callable=AsyncMock,
            return_value=([], 0),
        ), patch(
            "app.services.search.multi_source._search_olx_body",
            new_callable=AsyncMock,
            return_value=PaginatedListings(
                items=[fresh, old],
                total=2,
                page=1,
                per_page=500,
                pages=1,
            ),
        ), patch(
            "app.services.search.multi_source._fetch_source_pool",
            new_callable=AsyncMock,
            return_value=PaginatedListings(
                items=[], total=0, page=1, per_page=500, pages=0
            ),
        ):
            slots, nav_total, _market_total, _statuses = await build_live_search_pool(
                SearchFilters(brand="Hyundai", published_older_than_days=15),
                sort_by="newest",
                max_ids=50,
                olx_enrich_details=False,
            )
        return slots, nav_total

    slots, nav_total = asyncio.run(run())
    assert nav_total == 1
    assert len(slots) == 1
    assert slots[0].get("s") == "o"
