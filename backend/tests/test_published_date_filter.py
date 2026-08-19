from datetime import datetime, timedelta, timezone

from app.core.timezone import KYIV_TZ
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
    now = datetime(2026, 8, 19, 12, 0, tzinfo=KYIV_TZ)
    items = [
        _listing("old", now - timedelta(days=10)),
        _listing("fresh", now - timedelta(days=1)),
    ]
    filters = SearchFilters(published_within_days=3)
    result = _filter_listings_by_published_filters(items, filters)
    assert [item.id for item in result] == ["fresh"]
