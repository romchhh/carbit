from app.services.lubeavto.mapper import car_to_listing, filters_to_catalog_path
from app.services.lubeavto.parser import parse_catalog_page
from app.schemas.schemas import SearchFilters

SAMPLE_HTML = """
<html><body>
<p>Знайдено 1 результат</p>
<div>
  <a href="/store/instore/501">
    <img src="https://storage-lavto.example/car.jpg" />
    <h4>Audi A4 2018</h4>
  </a>
  <span>WAUZZZ8K9KA123456</span>
  <span>19 500 $</span>
  <span>93 тис. км</span>
  <span>Бензин</span>
  <span>2.0 л</span>
  <span>2018</span>
  <span>Автомат</span>
  <span>Повний</span>
</div>
</body></html>
"""


def test_parse_catalog_page_extracts_card():
    cars, total = parse_catalog_page(SAMPLE_HTML, catalog="instore")
    assert total == 1
    assert len(cars) == 1
    car = cars[0]
    assert car.car_id == 501
    assert car.brand == "Audi"
    assert car.model == "A4"
    assert car.year == 2018
    assert car.price_usd == 19500
    assert car.mileage_km == 93000
    assert car.vin == "WAUZZZ8K9KA123456"


def test_car_to_listing_maps_core_fields():
    cars, _ = parse_catalog_page(SAMPLE_HTML)
    listing = car_to_listing(cars[0])
    assert listing.id == "lubeavto_501"
    assert listing.source == "lubeavto"
    assert listing.brand == "Audi"
    assert listing.model == "A4"
    assert listing.vin == "WAUZZZ8K9KA123456"
    assert listing.region == "Львів"
    assert listing.seller_type == "dealer"


def test_filters_to_catalog_path_brand_model():
    path = filters_to_catalog_path(
        SearchFilters(brand="Audi", model="A4"),
        catalog="instore",
    )
    assert path == "store/instore/audi/a4"
