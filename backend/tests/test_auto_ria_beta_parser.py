from app.services.auto_ria_beta.mapper import car_to_listing
from app.services.auto_ria_beta.parser import ScrapedCar, parse_listing_details


LISTING_HTML = """
<script type="application/ld+json">
{"@context":"http://schema.org/","@type":"Vehicle","name":"BYD Song Plus 2024",
 "brand":{"@type":"Brand","name":"BYD"},"model":"Song Plus",
 "vehicleIdentificationNumber":"LGXCE4CB3R0672315","productionDate":"2024",
 "color":"Білий","fuelType":"Електро","vehicleTransmission":"Автомат",
 "description":"Не бувала в ДТП.","bodyType":"Позашляховик / Кросовер",
 "numberOfDoors":4,"mileageFromOdometer":{"@type":"QuantitativeValue","value":52000},
 "offers":{"@type":"Offer","priceCurrency":"USD","price":25950}}
</script>
{"id":"badgesPlateNumber","isHide":false,"elements":[{"type":"Text","content":"AB 7875 YA"}]}
{"id":"badgesVin","isHide":false,"elements":[{"type":"Text","content":"LGXCE4CB3R0672315"}]}
{"id":"badgesOrderFrom","isHide":false,"elements":[{"type":"Text","content":"Пригнано з Китаю"}]}
{"id":"descEngineEngine","isHide":false,"elements":[{"content":"Електро"}]}
{"id":"descTransmissionTransmission","isHide":false,"elements":[{"content":"Автомат"}]}
{"id":"descDriveTypeDriveType","isHide":false,"elements":[{"content":"Передній"}]}
{"id":"descColorColor","isHide":false,"elements":[{"content":"Білий"}]}
{"id":"descCharacteristicsValue","isHide":false,"elements":[{"content":"Позашляховик / Кросовер  •  4 дверей  •  5 місць"}]}
{"id":"descSecurityValue","isHide":false,"elements":[{"content":"ABS  •  ESP"}]}
{"id":"descDescription","isHide":false,"elements":[{"content":"Не бувала в ДТП."}]}
{"id":"sellerInfoUserName","isHide":false,"elements":[{"content":"Олена"}]}
{"id":"sellerInfoDia","isHide":false,"elements":[{"content":"Власник авто. Підтверджено через Дію"}]}
{"id":"verifyingsVertitle","isHide":false,"elements":[{"content":"Перевірено AUTO.RIA по VIN-коду"}]}
{"id":"verifyingsProvenDamageName0","isHide":false,"elements":[{"content":"ДТП"}]}
{"id":"verifyingsProvenDamageText00","isHide":false,"elements":[{"content":"Немає офіційно зареєстрованих"}]}
{"id":"verifyingsNaisName0","isHide":false,"elements":[{"content":"Тип обтяження"}]}
{"id":"verifyingsNaisText00","isHide":false,"elements":[{"content":"не виявлено"}]}
{"id":"elDescAccumCapacityValue","isHide":false,"elements":[{"content":"87 кВт-год"}]}
"""

USA_HTML = """
{"id":"badgesOrderFrom","isHide":false,"elements":[{"content":"Пригнано з США"}]}
{"id":"badgesDamaged","isHide":false,"elements":[{"content":"Був у ДТП"}]}
{"id":"badgesVin","isHide":false,"elements":[{"content":"1N4AL3AP8JC123456"}]}
{"id":"badgesPlateNumber","isHide":false,"elements":[{"content":"KA 0007 XB"}]}
"""


def test_parse_listing_details_extracts_vin_plate_and_flags():
    car = ScrapedCar(car_id=40307001, url="https://auto.ria.com/uk/auto_byd_song-plus_40307001.html")
    details = parse_listing_details(LISTING_HTML, car)

    assert car.vin == "LGXCE4CB3R0672315"
    assert car.plate == "AB 7875 YA"
    assert car.year == 2024
    assert car.fuel == "Електро"
    assert car.transmission == "Автомат"
    assert car.drive == "Передній"
    assert car.color == "Білий"
    assert car.seller_name == "Олена"
    assert car.mileage_km == 52000
    assert car.price_usd == 25950
    assert details["import_origin"] == "Пригнано з Китаю"
    assert details["usa_import"] is False
    assert details["had_accident"] is False
    assert details["vin_check"]["accidents_registered"] == "Немає офіційно зареєстрованих"
    assert details["electric"]["battery_capacity"] == "87 кВт-год"
    assert details["options"]["Безпека"] == ["ABS", "ESP"]


def test_parse_usa_and_accident_badges():
    car = ScrapedCar(car_id=1, url="https://auto.ria.com/uk/auto_nissan_altima_1.html")
    details = parse_listing_details(USA_HTML, car)
    assert details["usa_import"] is True
    assert details["had_accident"] is True
    assert car.vin == "1N4AL3AP8JC123456"
    assert "KA" in (car.plate or "")


def test_car_to_listing_maps_identity_and_flags():
    car = ScrapedCar(car_id=40307001, url="https://auto.ria.com/uk/auto_byd_song-plus_40307001.html")
    parse_listing_details(LISTING_HTML, car)
    listing = car_to_listing(car, brand_hint="BYD")

    assert listing.vin == "LGXCE4CB3R0672315"
    assert listing.plate == "AB 7875 YA"
    assert listing.vin_checked is True
    assert listing.vin_check_url == "https://auto.ria.com/vin-check/auto/40307001/"
    assert listing.seller_name == "Олена"
    assert listing.usa_import is False
    assert listing.had_accident is False
    assert listing.source_data["VIN"] == "LGXCE4CB3R0672315"
    assert listing.source_data["plateNumber"] == "AB 7875 YA"
    assert listing.source_data["ria_page_badges"]["usa_import"] is False


def test_search_card_parses_fuel_volume_drive_and_badges():
    html = (
        '<html><body>'
        '<a href="/uk/auto_bmw_x5_123456.html">'
        "BMW X5 2020 25 000 $ • 1 000 000 грн 80 тис. км Бензин, 3 л. Автомат Передній "
        "Позашляховик / Кросовер Київ Перевірений VIN Був у ДТП Пригнано з США"
        "</a>"
        '<div>1 пропозиція</div>'
        "</body></html>"
    )
    from app.services.auto_ria_beta.parser import parse_search_page

    cars, _ = parse_search_page(html)
    assert cars
    car = cars[0]
    listing = car_to_listing(car, brand_hint="BMW")
    assert "3" in (car.fuel or "")
    assert listing.engine_volume_l == 3.0
    assert listing.source_data["autoData"]["driveName"] == "Передній"
    assert listing.source_data["subCategoryName"].startswith("Позашляховик")
    assert listing.vin_checked is True
    assert listing.had_accident is True
    assert listing.usa_import is True
    assert listing.vin is None
    assert car.city == "Київ"
    assert listing.region == "Київ"


def test_search_page_parses_newauto_dealer_cards():
    html = (
        '<html><body>'
        '<script>{"id":"sortButtonContentCount","isHide":false,"elements":[{"type":"Text","content":"205 пропозицій"}]}</script>'
        '<a href="/uk/newauto/auto-zeekr-007-gt-2071226.html">'
        "В наявності Офіційний дилер ТОП 11 Новий Zeekr 007 GT 2026 "
        "45 555 $ · 2 031 297 грн Без пробігу 825 км Електро Київ"
        "</a>"
        '<a href="/uk/auto_zeekr_001_39830536.html">'
        "Zeekr 001 2025 55 000 $ · 2 464 000 грн 1 тис. км Електро Київ"
        "</a>"
        "</body></html>"
    )
    from app.services.auto_ria_beta.parser import parse_search_page

    cars, total = parse_search_page(html)
    assert total == 205
    assert len(cars) == 2
    new_car = next(car for car in cars if car.is_new)
    used_car = next(car for car in cars if not car.is_new)
    assert new_car.car_id == 2071226
    assert new_car.is_dealer is True
    assert new_car.year == 2026
    assert new_car.mileage_km == 825
    listing = car_to_listing(new_car, brand_hint="Zeekr")
    assert listing.id == "new_auto_ria_2071226"
    assert listing.source == "auto_ria"
    assert listing.is_new is True
    assert new_car.city == "Київ"
    assert used_car.city == "Київ"
    assert used_car.car_id == 39830536
    used_listing = car_to_listing(used_car, brand_hint="Zeekr")
    assert used_listing.id == "auto_ria_39830536"


def test_search_card_city_from_photo_alt_locative():
    html = (
        '<html><body>'
        '<a href="/uk/auto_bmw_x5_111.html">'
        '<img alt="Позашляховик / Кросовер BMW X5 2015 в Львові" src="https://cdn.example/x.jpg">'
        "BMW X5 2015 20 000 $ • 800 000 грн"
        "</a>"
        "</body></html>"
    )
    from app.services.auto_ria_beta.parser import parse_search_page

    cars, _ = parse_search_page(html)
    assert cars[0].city == "Львів"


def test_listings_from_cars_collapses_identical_newauto_stock():
    from app.schemas.schemas import SearchFilters
    from app.services.auto_ria_beta.mapper import listings_from_cars

    cars = [
        ScrapedCar(
            car_id=2073874,
            url="https://auto.ria.com/uk/newauto/auto-zeekr-7x-2073874.html",
            brand="Zeekr",
            model="7X",
            year=2026,
            price_usd=54465,
            mileage_km=543,
            is_new=True,
        ),
        ScrapedCar(
            car_id=2084883,
            url="https://auto.ria.com/uk/newauto/auto-zeekr-7x-2084883.html",
            brand="Zeekr",
            model="7X",
            year=2026,
            price_usd=54465,
            mileage_km=543,
            is_new=True,
        ),
        ScrapedCar(
            car_id=2084920,
            url="https://auto.ria.com/uk/newauto/auto-zeekr-7x-2084920.html",
            brand="Zeekr",
            model="7X",
            year=2026,
            price_usd=61100,
            mileage_km=715,
            is_new=True,
        ),
    ]
    listings = listings_from_cars(cars, SearchFilters(), sort_by="price_asc")
    assert len(listings) == 2
    assert {item.id for item in listings} == {
        "new_auto_ria_2073874",
        "new_auto_ria_2084920",
    }


def test_parse_total_count_ignores_empty_space_match():
    from app.services.auto_ria_beta.parser import parse_total_count

    html = "<html><body> пропозицій <script>{\"id\":\"sortButtonContentCount\",\"elements\":[{\"content\":\"512 пропозицій\"}]}</script></body></html>"
    assert parse_total_count(html) == 512
    assert parse_total_count("<p>   пропозицій</p>") == 0


def test_search_card_vin_present_is_not_treated_as_vin():
    listing = car_to_listing(
        ScrapedCar(
            car_id=1,
            url="https://auto.ria.com/uk/auto_bmw_x5_1.html",
            brand="BMW",
            vin="present",
            details={"vin_checked": True, "usa_import": True, "had_accident": True},
        )
    )
    assert listing.vin is None
    assert listing.vin_checked is True
    assert listing.usa_import is True
    assert listing.had_accident is True
