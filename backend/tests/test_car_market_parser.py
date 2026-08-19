from app.services.car_market.mapper import car_to_listing, filters_to_search_params, resolve_brand_id
from app.services.car_market.parser import parse_catalog_page
from app.schemas.schemas import SearchFilters

SAMPLE_HTML = """
<html><body>
<p>Знайдено 2 авто</p>
<span>На майданчику</span>
<div class="group bg-surface-50 rounded-2xl">
  <a href="/auto/volkswagen-passat-2018-12345">
    <img src="/uploads/cars/1/photo.webp" alt="Volkswagen Passat" />
  </a>
  <a href="/auto/volkswagen-passat-2018-12345">
    Volkswagen Passat 2018 12 500$ 180 тис.км Автомат Дизель 2.00 л Київ
  </a>
</div>
<span>19 серп.</span>
<a href="/auto/audi-a4-2016-67890">
  Audi A4 2016 9 800$ 220 тис.км Ручна / Механіка Бензин 1.80 л Одеса
</a>
</body></html>
"""


def test_parse_catalog_page_extracts_cars():
    cars, total = parse_catalog_page(SAMPLE_HTML)
    assert total == 2
    assert len(cars) == 2
    assert cars[0].title == "Volkswagen Passat"
    assert cars[0].year == 2018
    assert cars[0].price_usd == 12500
    assert cars[0].mileage_km == 180000
    assert cars[0].listing_type == "На майданчику"
    assert cars[0].car_id == 12345


def test_car_to_listing_maps_listing_out():
    cars, _ = parse_catalog_page(SAMPLE_HTML)
    listing = car_to_listing(cars[0], brand_hint="Volkswagen")
    assert listing.id == "car_market_12345"
    assert listing.source == "car_market"
    assert listing.brand == "Volkswagen"
    assert listing.model == "Passat"
    assert listing.currency == "USD"
    assert listing.price == 12500
    assert listing.images == ["https://car-market.net/uploads/cars/1/photo.webp"]


def test_resolve_brand_id_and_filters():
    assert resolve_brand_id("Audi") == "6628"
    params = filters_to_search_params(
        SearchFilters(brand="Volkswagen", price_from=5000, fuel=["Дизель"]),
        page=1,
    )
    assert params["brands"] == "6560"
    assert params["min_price"] == "5000"
    assert params["fuels[]"] == "2"
