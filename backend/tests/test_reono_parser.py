from app.services.reono.images import extract_card_image_urls, parse_detail_images
from app.services.reono.dates import parse_reono_updated_text
from app.services.reono.detail import parse_detail_published_at
from app.services.reono.mapper import car_to_listing
from app.services.reono.parser import ReonoCar, parse_catalog_page
from app.core.timezone import KYIV_TZ
from datetime import datetime

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

PICTURE_CARD = """
<article data-announcement-id="63904" data-announcement-brand="BMW" data-announcement-model="X3">
  <div class="car-card__slide swiper-slide">
    <a href="https://reono.ua/bmw-x3-63904" data-announcement-link class="car-card__image-ibg">
      <picture class="carPicture srcAdded">
        <source srcset="https://reono.ua/dist/img/no_img.svg 1x, https://reono.ua/dist/img/no_img_large.svg 2x"
          data-srcset="https://stx.reono.ua/791/593/bmw-slide-a.jpg 1x, https://stx.reono.ua/1582/1186/bmw-slide-a.jpg 2x">
        <img loading="lazy" src="https://reono.ua/dist/img/no_img.svg"
          data-src="https://stx.reono.ua/720/516/bmw-slide-a.jpg" alt="BMW X3 2015">
      </picture>
    </a>
  </div>
</article>
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
    assert all("stx.reono.ua" in url for url in urls)
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
    assert all("stx.reono.ua" in url for url in listing.images)


def test_picture_card_extracts_srcset_and_data_src():
    from bs4 import BeautifulSoup

    card = BeautifulSoup(PICTURE_CARD, "html.parser").select_one("article")
    urls = extract_card_image_urls(card)
    assert len(urls) == 1
    assert "bmw-slide-a.jpg" in urls[0]
    assert "1582/1186" in urls[0]

    cars, _ = parse_catalog_page(PICTURE_CARD)
    assert len(cars) == 1
    listing = car_to_listing(cars[0])
    assert len(listing.images) == 1
    assert "stx.reono.ua" in listing.images[0]


def test_parse_detail_images_from_data_src():
    images = parse_detail_images(DETAIL_GALLERY)
    assert len(images) == 2
    assert all("stx.reono.ua" in url for url in images)


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


def test_parse_reono_updated_text():
    parsed = parse_reono_updated_text("Оновлено 19.08.2026")
    assert parsed == datetime(2026, 8, 19, 12, 0, tzinfo=KYIV_TZ)


def test_parse_reono_published_text():
    parsed = parse_reono_updated_text("Опубліковано 23.08.2025")
    assert parsed == datetime(2025, 8, 23, 12, 0, tzinfo=KYIV_TZ)


def test_car_to_listing_without_published_at_uses_placeholder():
    from app.services.reono.dates import REONO_UNKNOWN_PUBLISHED_AT

    cars, _ = parse_catalog_page(SAMPLE_CARD)
    listing = car_to_listing(cars[0])
    assert listing.published_at == REONO_UNKNOWN_PUBLISHED_AT
    assert "published_at" not in (listing.source_data.get("reono") or {})


def test_parse_detail_published_at_from_mvs_block():
    html = """
    <div class="characteristecs-car-main__body__info__mvs__date">
      Оновлено 05.03.2025
    </div>
    """
    parsed = parse_detail_published_at(html)
    assert parsed == datetime(2025, 3, 5, 12, 0, tzinfo=KYIV_TZ)


def test_parse_detail_plate_from_mvs_block():
    from app.services.reono.detail import parse_detail_plate

    html = """
    <div class="characteristecs-car-main__body__info__number">
      <div class="characteristecs-car-main__body__info__number__country">UA
        <div class="characteristecs-car-main__body__info__number__country__number">AA2459TP</div>
      </div>
    </div>
    """
    assert parse_detail_plate(html) == "AA 2459 TP"


def test_car_to_listing_uses_parsed_published_at():
    cars, _ = parse_catalog_page(SAMPLE_CARD)
    car = cars[0]
    car.published_at = datetime(2025, 3, 5, 12, 0, tzinfo=KYIV_TZ)
    listing = car_to_listing(car)
    assert listing.published_at == car.published_at
    assert listing.source_data["reono"]["published_at"] == car.published_at.isoformat()


def test_reono_needs_published_at_when_missing():
    from app.schemas.schemas import ListingOut
    from app.services.reono.service import _reono_needs_published_at

    listing = ListingOut(
        id="reono_1",
        source="reono",
        title="Test",
        brand="BMW",
        model="X5",
        year=2020,
        price=10000,
        currency="USD",
        mileage=50000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=[],
        url="https://reono.ua/test-1",
        seller_type="private",
        vin=None,
        source_data={"reono": {"car_id": 1}},
        price_history=[],
        is_duplicate=False,
        published_at=datetime(1970, 1, 1, 12, 0, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 9, 2, 12, 0, tzinfo=KYIV_TZ),
    )
    assert _reono_needs_published_at(listing) is True

    with_date = listing.model_copy(
        update={"source_data": {"reono": {"car_id": 1, "published_at": "2025-08-23T12:00:00+03:00"}}}
    )
    assert _reono_needs_published_at(with_date) is False
