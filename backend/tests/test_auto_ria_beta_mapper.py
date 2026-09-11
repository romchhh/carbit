from unittest.mock import AsyncMock, patch

from app.schemas.schemas import SearchFilters
from app.services.auto_ria_beta.mapper import car_to_listing, filters_to_html_params
from app.services.auto_ria_beta.parser import ScrapedCar
from app.services.search.multi_source import _listing_to_slot
from app.services.telegram_channels.mapper import listing_out_matches_filters


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
    assert listing.id == "auto_ria_40307001"
    assert listing.source == "auto_ria"
    assert listing.published_at is not None
    assert listing.found_at is not None


def test_html_listing_slot_keeps_card_for_api_hydrate():
    slot = _listing_to_slot(_sample_listing())
    assert slot["s"] == "r"
    assert slot["i"] == "40307001"
    assert "d" in slot
    assert slot["d"]["id"] == "auto_ria_40307001"
    assert slot["d"]["source"] == "auto_ria"


def test_html_params_kyiv_city_uses_site_geo_keys():
    async def run():
        with (
            patch(
                "app.services.auto_ria_beta.mapper.resolve_mark_id",
                new=AsyncMock(return_value=55280),
            ),
            patch(
                "app.services.auto_ria_beta.mapper.resolve_model_id",
                new=AsyncMock(return_value=64237),
            ),
            patch("app.services.auto_ria_beta.mapper.AutoRiaClient"),
        ):
            params = await filters_to_html_params(
                SearchFilters(brand="Zeekr", model="001", region="м. Київ"),
                page=0,
                size=20,
            )
        assert params["state[0]"] == 10
        assert params["city[0]"] == 10
        assert "state[0].id" not in params
        assert "city[0].id" not in params

    import asyncio

    asyncio.run(run())


def test_html_params_oblast_omits_city():
    async def run():
        with (
            patch(
                "app.services.auto_ria_beta.mapper.resolve_mark_id",
                new=AsyncMock(return_value=9),
            ),
            patch(
                "app.services.auto_ria_beta.mapper.resolve_model_id",
                new=AsyncMock(return_value=1),
            ),
            patch("app.services.auto_ria_beta.mapper.AutoRiaClient"),
        ):
            params = await filters_to_html_params(
                SearchFilters(brand="BMW", model="X5", region="Львівська область"),
                page=0,
                size=20,
            )
        assert params["state[0]"] == 5
        assert "city[0]" not in params
        assert "state[0].id" not in params

    import asyncio

    asyncio.run(run())


def test_html_card_from_lviv_does_not_match_kyiv_filter():
    lviv = car_to_listing(
        ScrapedCar(
            car_id=111,
            url="https://auto.ria.com/uk/auto_zeekr_001_111.html",
            brand="Zeekr",
            model="001",
            year=2024,
            price_usd=42000,
            city="Львів",
        ),
        brand_hint="Zeekr",
        model_hint="001",
    )
    kyiv = car_to_listing(
        ScrapedCar(
            car_id=222,
            url="https://auto.ria.com/uk/auto_zeekr_001_222.html",
            brand="Zeekr",
            model="001",
            year=2024,
            price_usd=42000,
            city="Київ",
        ),
        brand_hint="Zeekr",
        model_hint="001",
    )
    city_filters = SearchFilters(brand="Zeekr", model="001", region="м. Київ")
    oblast_filters = SearchFilters(brand="Zeekr", model="001", region="Київська область")
    assert listing_out_matches_filters(kyiv, city_filters)
    assert not listing_out_matches_filters(lviv, city_filters)
    assert listing_out_matches_filters(kyiv, oblast_filters)
    assert not listing_out_matches_filters(lviv, oblast_filters)
