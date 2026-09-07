from app.services.udrive.constants import udrive_listing_url


def test_udrive_listing_url_without_brand_slug():
    car_id = "2995AB35-8D3F-4289-BABF-FF9D939BCECE"
    assert (
        udrive_listing_url(car_id)
        == "https://udrive.com.ua/catalog/cars/2995ab35-8d3f-4289-babf-ff9d939bcece"
    )


def test_udrive_listing_url_matches_public_site_format():
    assert (
        udrive_listing_url("0490d522-1c2d-48cd-b2cb-7c8f38ac5320")
        == "https://udrive.com.ua/catalog/cars/0490d522-1c2d-48cd-b2cb-7c8f38ac5320"
    )
