from app.services.auto_ria_beta.mapper import car_to_listing
from app.services.auto_ria_beta.parser import ScrapedCar
from app.services.search.multi_source import _listing_to_slot


def _sample_listing():
    return car_to_listing(
        ScrapedCar(
            car_id=40307001,
            url="https://auto.ria.com/uk/auto_byd_song-plus_40307001.html",
            brand="byd",
            model="Song Plus",
            year=2023,
            price_usd=25000,
        ),
        brand_hint="BYD",
    )


def test_car_to_listing_has_required_datetimes():
    listing = _sample_listing()
    assert listing.id == "auto_ria_beta_40307001"
    assert listing.source == "auto_ria_beta"
    assert listing.published_at is not None
    assert listing.found_at is not None


def test_beta_listing_slot_is_not_paid_auto_ria_stub():
    slot = _listing_to_slot(_sample_listing())
    assert slot["s"] == "b"
    assert "d" in slot
    assert slot["d"]["id"] == "auto_ria_beta_40307001"
    assert slot["d"]["source"] == "auto_ria_beta"
