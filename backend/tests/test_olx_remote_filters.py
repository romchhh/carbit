"""OLX remote filters: базові + розширені + регіон."""

from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from app.schemas.schemas import SearchFilters
from app.services.olx.mapper import filters_to_olx_params
from app.services.olx.parser import (
    OlxSearchParams,
    build_offers_api_params,
    build_search_url,
)


class OlxRemoteFilterUrlTests(unittest.TestCase):
    def test_price_year_engine_in_html_url(self):
        params = OlxSearchParams(
            brand="toyota",
            currency="USD",
            price_from=5000,
            price_to=20000,
            year_from=2018,
            year_to=2022,
            engine_from=2.0,
            engine_to=3.0,
        )
        url = build_search_url(params)
        qs = parse_qs(urlparse(url).query)
        self.assertEqual(qs.get("search[filter_float_price:from]"), ["5000"])
        self.assertEqual(qs.get("search[filter_float_motor_year:from]"), ["2018"])
        self.assertEqual(qs.get("search[filter_float_motor_engine_size_litre:from]"), ["2.0"])

    def test_region_id_lviv_html_and_api(self):
        params = filters_to_olx_params(
            SearchFilters(brand="Toyota", region="Львівська область")
        )
        self.assertEqual(params.region_id, 5)
        self.assertIsNone(params.city_id)
        qs = parse_qs(urlparse(build_search_url(params)).query)
        self.assertEqual(qs.get("search[region_id]"), ["5"])
        api = build_offers_api_params(params)
        self.assertEqual(api.get("region_id"), "5")

    def test_region_alias_without_oblast_word(self):
        params = filters_to_olx_params(SearchFilters(brand="Toyota", region="Одеська"))
        self.assertEqual(params.region_id, 9)

    def test_kyiv_uses_city_id_not_region(self):
        for label in ("м. Київ", "Київ", "Kyiv"):
            params = filters_to_olx_params(SearchFilters(brand="Toyota", region=label))
            self.assertEqual(params.city_id, 268, label)
            self.assertIsNone(params.region_id, label)
            self.assertEqual(params.city_query, "kyiv", label)
            api = build_offers_api_params(params)
            self.assertEqual(api.get("city_id"), "268", label)
            # HTML не шле city_id (OLX ігнорує) — лише /q-kyiv/
            qs = parse_qs(urlparse(build_search_url(params)).query)
            self.assertIsNone(qs.get("search[city_id]"))
            self.assertIsNone(qs.get("search[region_id]"))

    def test_advanced_body_usa_accident_colors(self):
        params = filters_to_olx_params(
            SearchFilters(
                brand="Toyota",
                currency="USD",
                body_types=["Седан", "Хетчбек"],
                colors=["Чорний", "Білий"],
                fuel=["Бензин", "Дизель"],
                drivetrain=["Повний"],
                transmission=["Автомат", "Типтронік"],
                usa_import="show",
                accident="none",
                owners_max=1,
                seats_from=5,
                seats_to=5,
            )
        )
        self.assertEqual(params.body_enums, ["sedan", "hatchback"])
        self.assertEqual(params.color_enums, ["2", "1"])
        self.assertEqual(params.fuels, ["petrol", "diesel"])
        self.assertEqual(params.drivetrains, ["awd"])
        self.assertIn("automatic", params.transmissions)
        self.assertIn("tiptronic", params.transmissions)
        self.assertEqual(params.car_from_enums, ["usa"])
        self.assertIn("not-bit", params.condition_enums)
        self.assertIn("first-owner", params.condition_enums)

        qs = parse_qs(urlparse(build_search_url(params)).query)
        self.assertEqual(qs.get("search[filter_enum_car_body][0]"), ["sedan"])
        self.assertEqual(qs.get("search[filter_enum_car_body][1]"), ["hatchback"])
        self.assertEqual(qs.get("search[filter_enum_car_from][0]"), ["usa"])
        self.assertEqual(qs.get("search[filter_enum_color][0]"), ["2"])
        self.assertEqual(qs.get("search[filter_enum_fuel_type][0]"), ["542"])
        self.assertEqual(qs.get("search[filter_enum_drive_type][0]"), ["full"])
        self.assertEqual(qs.get("search[filter_enum_seats_num][0]"), ["5"])
        self.assertIn("not-bit", qs.get("search[filter_enum_condition][0]", []))

        api = build_offers_api_params(params)
        self.assertEqual(api.get("filter_enum_car_body[0]"), "sedan")
        self.assertEqual(api.get("filter_enum_car_from[0]"), "usa")
        self.assertTrue(params.has_remote_filters())

    def test_accident_had_and_zero_mileage(self):
        params = filters_to_olx_params(
            SearchFilters(brand="BMW", accident="had", zero_mileage=True)
        )
        self.assertEqual(params.condition_enums, ["after-an-accident"])
        self.assertEqual(params.mileage_to, 0)
        qs = parse_qs(urlparse(build_search_url(params)).query)
        self.assertEqual(qs.get("search[filter_enum_condition][0]"), ["after-an-accident"])
        self.assertEqual(qs.get("search[filter_float_motor_mileage_thou:to]"), ["0"])

    def test_tesla_path_with_price(self):
        params = filters_to_olx_params(
            SearchFilters(
                brand="Tesla",
                model="Model S",
                currency="UAH",
                price_from=100_000,
                price_to=1_000_000,
            )
        )
        url = build_search_url(params)
        self.assertIn("/tesla/q-tesla-model-s/", url)
        qs = parse_qs(urlparse(url).query)
        self.assertEqual(qs.get("search[filter_float_price:from]"), ["100000"])


if __name__ == "__main__":
    unittest.main()
