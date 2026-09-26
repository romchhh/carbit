from app.schemas.schemas import SearchFilters
from app.services.search.filter_multi import search_needs_client_listing_filter


def test_year_only_search_needs_client_filter():
    filters = SearchFilters(year_from=2007, year_to=2023)
    assert search_needs_client_listing_filter(filters) is True


def test_empty_search_does_not_need_client_filter():
    assert search_needs_client_listing_filter(SearchFilters()) is False


def test_brand_only_needs_client_filter():
    assert search_needs_client_listing_filter(SearchFilters(brand="BMW")) is True
