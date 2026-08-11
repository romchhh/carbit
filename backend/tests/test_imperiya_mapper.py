from app.services.imperiya.mapper import ad_to_listing, sort_to_imperiya


def test_sort_to_imperiya_newest():
    assert sort_to_imperiya("newest") == "date"
    assert sort_to_imperiya("price_asc") == "price_asc"


def test_ad_to_listing_maps_core_fields():
    listing = ad_to_listing(
        {
            "id": 51533,
            "url": "https://imperiya-auto.com.ua/listing/nissan-juke-51533",
            "title": "Nissan Juke",
            "productionYear": 2017,
            "make": "Nissan",
            "model": "Juke",
            "mileage": 60,
            "engineType": "Бензиновий",
            "transmission": "Варіатор",
            "engineVolume": "1.6",
            "price": {"usd": 13800, "uah": 621622},
            "images": [
                {
                    "url": "https://cdn.example/photo.avif",
                    "mediumUrl": "https://cdn.example/medium.avif",
                }
            ],
            "city": "Одеса",
            "region": "Одеська",
            "createdAt": "2026-08-10T15:24:16.713Z",
            "dealer": {"name": "Стиль-Авто", "slug": "styl-avto"},
        },
        currency="USD",
    )
    assert listing.id == "imperiya_51533"
    assert listing.source == "imperiya"
    assert listing.brand == "Nissan"
    assert listing.model == "Juke"
    assert listing.mileage == 60000
    assert listing.price == 13800
    assert listing.currency == "USD"
    assert listing.seller_type == "dealer"
    assert listing.seller_name == "Стиль-Авто"
    assert listing.seller_url == "https://imperiya-auto.com.ua/dealer/styl-avto"
    assert listing.images == ["https://cdn.example/medium.avif"]


def test_ad_to_listing_empty_engine_volume_electric():
    """Zeekr / електро: engineVolume='' не має ламати мапінг."""
    listing = ad_to_listing(
        {
            "id": 50185,
            "url": "https://imperiya-auto.com.ua/listing/zeekr-001-50185",
            "title": "Zeekr 001",
            "productionYear": 2025,
            "make": "Zeekr",
            "model": "001",
            "mileage": 2,
            "engineType": "Електро",
            "engineVolume": "",
            "price": {"usd": 45000, "uah": 1800000},
            "images": [],
            "city": "Київ",
            "region": "Київська",
            "createdAt": "2026-08-10T15:24:16.713Z",
        },
        currency="USD",
    )
    assert listing.brand == "Zeekr"
    assert listing.model == "001"
    assert listing.engine_volume_l is None
