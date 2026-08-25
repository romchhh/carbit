from app.services.reono.images import extract_card_image_urls, parse_detail_images
from app.services.reono.mapper import car_to_listing
from app.services.reono.parser import parse_catalog_page

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

LAZY_CARD = """
<article data-announcement-id="35012" data-announcement-brand="Audi" data-announcement-model="A4">
  <a data-announcement-link href="https://reono.ua/audi-a4-avant-35012">
    <span class="car-card__lazy-picture" data-image-normal="https://stx.reono.ua/360/258/token-a.jpg"
      data-image-large="https://stx.reono.ua/791/593/token-a.jpg">
      <img src="https://reono.ua/dist/img/no_img.svg" />
    </span>
    <span class="car-card__lazy-picture" data-image-normal="https://stx.reono.ua/360/258/token-b.jpg"
      data-image-large="https://stx.reono.ua/791/593/token-b.jpg">
      <img src="https://reono.ua/dist/img/no_img.svg" />
    </span>
  </a>
</article>
"""

DETAIL_GALLERY = """
<div class="description-car-main-big__wrapper">
  <div class="description-car-main-big__slide">
    <img loading="lazy" src="https://reono.ua/dist/img/no_img.svg"
      data-src="https://stx.reono.ua/791/593/token-a.jpg" />
  </div>
  <div class="description-car-main-big__slide">
    <img loading="lazy" src="https://reono.ua/dist/img/no_img.svg"
      data-src="https://stx.reono.ua/791/593/token-b.jpg" />
  </div>
</div>
<script type="application/ld+json">
{"@type":"Car","image":"https://stx.reono.ua/360/258/token-a.jpg"}
</script>
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


def test_lazy_card_extracts_data_image_urls():
    from bs4 import BeautifulSoup

    card = BeautifulSoup(LAZY_CARD, "html.parser").select_one("article")
    urls = extract_card_image_urls(card)
    assert len(urls) == 2
    assert all("791/593" in url for url in urls)
    assert "token-a.jpg" in urls[0]
    assert "token-b.jpg" in urls[1]


def test_car_to_listing_maps_listing_out():
    cars, _ = parse_catalog_page(SAMPLE_CARD)
    listing = car_to_listing(cars[0])
    assert listing.id == "reono_113843"
    assert listing.source == "reono"
    assert listing.price == 13700
    assert listing.region == "Рівне"
    assert listing.images == ["https://stx.reono.ua/photo.jpg"]


def test_car_to_listing_includes_lazy_gallery_from_card():
    cars, _ = parse_catalog_page(LAZY_CARD)
    assert len(cars) == 1
    listing = car_to_listing(cars[0])
    assert len(listing.images) == 2
    assert all("791/593" in url for url in listing.images)


def test_parse_detail_images_from_data_src():
    images = parse_detail_images(DETAIL_GALLERY)
    assert len(images) == 2
    assert all("791/593" in url for url in images)


def test_filters_to_catalog_path_kyiv_city():
    from app.schemas.schemas import SearchFilters
    from app.services.reono.mapper import filters_to_catalog_path

    path = filters_to_catalog_path(
        SearchFilters(brand="Audi", model="A5", region="м. Київ"),
        page=1,
    )
    assert path == "legkovoe-avto/kievskaya-oblast/kiev/audi/a5"


def test_filters_to_catalog_path_kyiv_oblast():
    from app.schemas.schemas import SearchFilters
    from app.services.reono.mapper import filters_to_catalog_path

    path = filters_to_catalog_path(
        SearchFilters(brand="Volkswagen", model="Passat", region="Київська область"),
        page=2,
    )
    assert path == "legkovoe-avto/kievskaya-oblast/volkswagen/passat/page=2"


def test_filters_to_catalog_path_legacy_kyiv_label():
    from app.schemas.schemas import SearchFilters
    from app.services.reono.mapper import filters_to_catalog_path

    path = filters_to_catalog_path(
        SearchFilters(brand="Volkswagen", model="Passat", region="м. Київ"),
        page=2,
    )
    assert path.startswith("legkovoe-avto/kievskaya-oblast/kiev/")
    assert "volkswagen" in path
    assert "passat" in path
    assert path.endswith("page=2")
