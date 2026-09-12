import asyncio
from unittest.mock import AsyncMock, patch

from app.services.lubeavto.parser import LubeAvtoCar, parse_catalog_page
from app.services.lubeavto.mapper import car_to_listing, filters_to_catalog_path
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


def test_parse_result_total_ignores_html_comments():
    html = "Знайдено<!-- --> <!-- -->1<!-- --> результатів"
    from app.services.lubeavto.parser import _parse_result_total

    assert _parse_result_total(html) == 1


def test_parse_auction_href_and_empty_mileage():
    html = """
    <html><body>
    <a href="/store/auction/44970651-2">
      <h4>Zeekr 001 2026</h4>
    </a>
    <span> - тис. км</span>
    <span>21 000 $</span>
    </body></html>
    """
    cars, total = parse_catalog_page(html, catalog="auction")
    assert total == 1
    assert len(cars) == 1
    assert cars[0].car_id == "44970651-2"
    assert cars[0].title.startswith("Zeekr")
    assert cars[0].mileage_km is None


def test_catalog_paths_do_not_fall_back_to_root():
    from app.services.lubeavto.service import _catalog_paths

    paths = _catalog_paths(SearchFilters(brand="Zeekr", model="001"), "instore")
    assert paths == ["store/instore/zeekr/001", "store/instore/zeekr"]
    assert "store/instore" not in paths


def test_search_uses_in_transit_catalog_not_full_lot():
    from app.services.lubeavto.service import _search_lubeavto_body

    zeekr = LubeAvtoCar(
        title="ZEEKR 001 2026",
        brand="ZEEKR",
        model="001",
        year=2026,
        price_usd=21000,
        mileage_km=8000,
        mileage_raw="8 тис. км",
        fuel="Електро",
        engine=None,
        transmission="Автомат",
        drive="Повний",
        vin=None,
        badge="НОВЕ",
        url="https://lubeavto.com.ua/store/instoreusers/27682",
        image_url=None,
        car_id=27682,
        catalog="instoreusers",
    )

    async def fetch(path, *, page_number=0, catalog="instore"):
        if catalog == "instoreusers" and "zeekr" in path:
            return [zeekr], 1
        return [], 0

    async def run():
        with patch("app.services.lubeavto.service.LubeAvtoClient") as client_cls:
            client_cls.return_value.fetch_catalog = AsyncMock(side_effect=fetch)
            return await _search_lubeavto_body(
                SearchFilters(
                    brand="Zeekr",
                    model="001",
                    year_from=2024,
                    year_to=2026,
                    sources=["lubeavto"],
                ),
                per_page=20,
            )

    page = asyncio.run(run())
    assert len(page.items) == 1
    assert page.items[0].title == "ZEEKR 001 2026"
    assert page.total == 1
    assert page.market_total == 1


