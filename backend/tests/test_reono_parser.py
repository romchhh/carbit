from app.services.reono.mapper import car_to_listing, filters_to_catalog_path
from app.services.reono.parser import parse_catalog_page
from app.schemas.schemas import SearchFilters

SAMPLE_CARD = """
<article class="car-card" data-announcement-id="113843"
  data-announcement-brand="Nissan" data-announcement-model="Rogue"
  data-analytics-context='{"year_range":"2017","price_range":"13700","location_name":"Рівне","fuel_type":"petrol","gearbox_type":"variator","mileage_range":"149"}'>
  <a class="car-card__title" href="https://reono.ua/nissan-rogue-113843">Nissan Rogue 2017</a>
  <div class="subtitle-car-card__item _icon-map-pin">Рівне</div>
  <div class="car-card__tag tag-autocard">149 000 км</div>
  <div class="car-card__tag tag-autocard">Варіатор</div>
  <div class="car-card__tag tag-autocard">Бензин, 2.5</div>
  <span data-price-usd="13700">13700 $</span>
  <span data-price-uah="612398">612398 ₴</span>
  <img src="https://stx.reono.ua/photo.jpg" />
</article>
<p>Найдено 19655 авто</p>
"""


def test_parse_catalog_page_extracts_car_card():
    cars, total = parse_catalog_page(SAMPLE_CARD)
    assert total == 19655
    assert len(cars) == 1
    assert cars[0].car_id == 113843
    assert cars[0].brand == "Nissan"
    assert cars[0].model == "Rogue"
    assert cars[0].year == 2017
    assert cars[0].price_usd == 13700
    assert cars[0].mileage_km == 149000


def test_car_to_listing_maps_listing_out():
    cars, _ = parse_catalog_page(SAMPLE_CARD)
    listing = car_to_listing(cars[0])
    assert listing.id == "reono_113843"
    assert listing.source == "reono"
    assert listing.price == 13700
    assert listing.region == "Рівне"


def test_filters_to_catalog_path_kyiv_city():
    path = filters_to_catalog_path(
        SearchFilters(brand="Audi", model="A5", region="м. Київ"),
        page=1,
    )
    assert path == "legkovoe-avto/kievskaya-oblast/kiev/audi/a5"


def test_filters_to_catalog_path_kyiv_oblast():
    path = filters_to_catalog_path(
        SearchFilters(brand="Volkswagen", model="Passat", region="Київська область"),
        page=2,
    )
    assert path == "legkovoe-avto/kievskaya-oblast/volkswagen/passat/page=2"


def test_filters_to_catalog_path_legacy_kyiv_label():
    path = filters_to_catalog_path(
        SearchFilters(brand="Volkswagen", model="Passat", region="м. Київ"),
        page=2,
    )
    assert path.startswith("legkovoe-avto/kievskaya-oblast/kiev/")
    assert "volkswagen" in path
    assert "passat" in path
    assert path.endswith("page=2")
