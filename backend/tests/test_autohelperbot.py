"""Тести парсера autohelperbot (без живого Playwright)."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.autohelperbot.scraper import (
    INPUT_SELECTOR,
    abs_autohelper_url,
    build_result_from_dump,
    parse_specs,
    pick_car_url,
    pick_photos,
    pick_report_links,
)
from app.services.autohelperbot.service import map_auction_payload
from app.services.baza_gai.errors import BazaGaiNotFound
from app.services.baza_gai.service import lookup_vin_check
from app.schemas.schemas import VinAuctionOut, VinCheckOut


SAMPLE_BODY = """
2018 Nissan Rogue
Пробег 54,321 mi 87400km
Дата продажи (UTC) 12.03.2024 18:40
Цена продажи: $ 4200 USD
Записей о продаже: 2
Двигатель 2.5L 4cyl
Цвет WHITE
Коробка передач Automatic
Топливо Gasoline
Привод 4x4
Ключи Yes
Стоимость ремонта $ 8900 USD
Рыночная стоимость $ 14500 USD
Основное повреждение
Front End
Внешнее состояние Normal Wear
Средняя цена: $ 12100 USD
"""

SAMPLE_DUMP = {
    "url": "https://autohelperbot.com/car/5N1AT2MV9JC767550_81234567",
    "title": "2018 Nissan Rogue\n5N1AT2MV9JC767550",
    "body": SAMPLE_BODY,
    "meta_description": "Nissan Rogue | повреждение: Front End | Copart",
    "og_image": "https://cdn.example.com/og.jpg",
    "hrefs": [
        "/check_vin?vin=5N1AT2MV9JC767550",
        "https://www.copart.com/lot/81234567",
        "https://www.iaai.com/Vehicle?id=1",
        "/check-autocheck?vin=5N1AT2MV9JC767550",
        "/check-windowsticker?vin=5N1AT2MV9JC767550",
        "https://example.com/other",
    ],
    "images": [
        {
            "url": "https://cdn.example.com/5N1AT2MV9JC767550-590.jpg",
            "alt": "Front 5N1AT2MV9JC767550",
        },
        {"url": "https://cdn.example.com/other-590.jpg", "alt": "unrelated"},
        {
            "url": "https://cdn.example.com/5N1AT2MV9JC767550-590.jpg",
            "alt": "dup",
        },
    ],
}


class UrlHelpersTests(unittest.TestCase):
    def test_abs_url(self):
        self.assertEqual(
            abs_autohelper_url("/car/ABC"),
            "https://autohelperbot.com/car/ABC",
        )
        self.assertEqual(
            abs_autohelper_url("https://autohelperbot.com/car/X"),
            "https://autohelperbot.com/car/X",
        )
        self.assertEqual(abs_autohelper_url(""), "")

    def test_pick_car_url_from_current(self):
        url = "https://autohelperbot.com/car/5N1AT2MV9JC767550_1"
        self.assertEqual(pick_car_url(url, [], "5N1AT2MV9JC767550"), url)

    def test_pick_car_url_prefers_matching_vin(self):
        hrefs = [
            "/car/AAAAAAAAAAAAAAA01_1",
            "https://autohelperbot.com/car/5N1AT2MV9JC767550_99",
        ]
        self.assertEqual(
            pick_car_url("https://autohelperbot.com/car-search", hrefs, "5N1AT2MV9JC767550"),
            "https://autohelperbot.com/car/5N1AT2MV9JC767550_99",
        )

    def test_pick_car_url_empty(self):
        self.assertIsNone(pick_car_url("https://autohelperbot.com/car-search", ["/about"], "X" * 17))


class ParseSpecsTests(unittest.TestCase):
    def test_parses_auction_fields(self):
        specs = parse_specs(SAMPLE_BODY)
        self.assertEqual(specs["mileage"], "54,321 mi")
        self.assertEqual(specs["mileage_km"], "87400km")
        self.assertTrue(specs["sale_date"].startswith("12.03.2024"))
        self.assertIn("4200", specs["sale_price"])
        self.assertEqual(specs["sale_records"], "2")
        self.assertEqual(specs["engine"], "2.5L 4cyl")
        self.assertEqual(specs["color"], "WHITE")
        self.assertEqual(specs["keys"], "Yes")
        self.assertIn("8900", specs["repair_cost"])

    def test_damage_from_meta_fallback(self):
        specs = parse_specs("Nissan Rogue", "повреждение: Rear | Copart")
        self.assertEqual(specs["primary_damage"], "Rear")


class PhotosAndLinksTests(unittest.TestCase):
    def test_photos_filter_by_vin_and_dedupe(self):
        photos = pick_photos(SAMPLE_DUMP["images"], "5N1AT2MV9JC767550")
        self.assertEqual(len(photos), 1)
        self.assertIn("5N1AT2MV9JC767550-590.jpg", photos[0]["url"])
        self.assertEqual(photos[0]["caption"], "Front")

    def test_iaai_s2_photos_keep_all_matching_vin(self):
        vin = "KMHGN4JE3GU111299"
        images = [
            {"url": f"https://s2.autohelperbot.com/{vin}-111.jpg", "alt": f"Front vin: {vin}"},
            {"url": f"https://s2.autohelperbot.com/{vin}-222.jpg", "alt": ""},
            {"url": f"https://s2.autohelperbot.com/{vin}-111.jpg", "alt": "dup"},
            {"url": "https://s2.autohelperbot.com/OTHERVIN123456789-333.jpg", "alt": "other"},
            {"url": "https://autohelperbot.com/img/langs/ru.svg", "alt": "ru"},
            {
                "url": "https://img.autohelperbot.com/2026_08/KMHGN4JE3GU122108-140.jpeg",
                "alt": "related",
            },
        ]
        photos = pick_photos(images, vin)
        self.assertEqual(len(photos), 2)
        self.assertTrue(all(vin in p["url"] for p in photos))

    def test_report_links(self):
        links = pick_report_links(SAMPLE_DUMP["hrefs"])
        self.assertIn("vin=5N1AT2MV9JC767550", links["carhistory"])
        self.assertIn("copart.com", links["copart"])
        self.assertIn("iaai.com", links["iaai"])
        self.assertIn("autocheck", links["autocheck"])
        self.assertIn("windowsticker", links["window_sticker"])


class BuildResultTests(unittest.TestCase):
    def test_dump_to_result(self):
        data = build_result_from_dump(SAMPLE_DUMP)
        self.assertEqual(data["vin"], "5N1AT2MV9JC767550")
        self.assertEqual(data["lot_id"], "81234567")
        self.assertEqual(data["title"], "2018 Nissan Rogue")
        self.assertTrue(data["specs"].get("engine"))
        self.assertEqual(data["photos_count"], 1)
        self.assertIn("copart", data["links"])
        mapped = map_auction_payload(data, vin="5N1AT2MV9JC767550")
        self.assertEqual(mapped.vin, "5N1AT2MV9JC767550")
        self.assertEqual(mapped.lot_id, "81234567")
        self.assertEqual(mapped.source, "autohelperbot")
        self.assertTrue(mapped.copart_url)
        self.assertEqual(len(mapped.photos), 1)


class ScraperContractTests(unittest.TestCase):
    def test_no_networkidle_or_fixed_sleeps(self):
        from app.services.autohelperbot import scraper as scraper_mod

        hot_path = "\n".join(
            inspect.getsource(fn)
            for fn in (
                scraper_mod.scrape_vin_auction,
                scraper_mod._find_car_url,
                scraper_mod._extract_data,
                scraper_mod._wait_for_car_or_empty,
            )
        )
        self.assertNotIn("networkidle", hot_path)
        self.assertNotIn("wait_for_timeout", hot_path)
        self.assertNotIn("delay=80", hot_path)
        self.assertIn("domcontentloaded", hot_path)
        self.assertIn("fill(", hot_path)

    def test_input_selector_is_combined(self):
        self.assertIn(",", INPUT_SELECTOR)
        self.assertIn("VIN", INPUT_SELECTOR)

    def test_auction_timeout_is_bounded(self):
        self.assertLessEqual(settings.VIN_AUCTION_TIMEOUT_SECONDS, 45.0)


class LookupCombinesSourcesTests(unittest.IsolatedAsyncioTestCase):
    async def test_baza_result_survives_auction_failure(self):
        baza = VinCheckOut(
            vin="5N1AT2MV9JC767550",
            vendor="Nissan",
            model="Rogue",
            is_stolen=False,
            registrations_count=1,
            source_url="https://baza-gai.com.ua/vin/5N1AT2MV9JC767550",
        )
        with (
            patch(
                "app.services.baza_gai.service._lookup_baza_only",
                AsyncMock(return_value=baza),
            ),
            patch(
                "app.services.baza_gai.service.lookup_vin_auction",
                AsyncMock(side_effect=RuntimeError("browser hung")),
            ),
            patch("app.services.baza_gai.service.settings") as mock_settings,
        ):
            mock_settings.VIN_AUCTION_CHECK_ENABLED = True
            mock_settings.VIN_AUCTION_TIMEOUT_SECONDS = 45.0
            out = await lookup_vin_check("5N1AT2MV9JC767550")
        self.assertEqual(out.vendor, "Nissan")
        self.assertIsNone(out.auction)

    async def test_auction_only_when_baza_missing(self):
        auction = VinAuctionOut(
            vin="5N1AT2MV9JC767550",
            title="2018 Nissan Rogue",
            page_url="https://autohelperbot.com/car/5N1AT2MV9JC767550",
            primary_damage="Front End",
            photo_url="https://cdn.example.com/p.jpg",
        )
        with (
            patch(
                "app.services.baza_gai.service._lookup_baza_only",
                AsyncMock(side_effect=BazaGaiNotFound("5N1AT2MV9JC767550")),
            ),
            patch(
                "app.services.baza_gai.service.lookup_vin_auction",
                AsyncMock(return_value=auction),
            ),
            patch("app.services.baza_gai.service.settings") as mock_settings,
        ):
            mock_settings.VIN_AUCTION_CHECK_ENABLED = True
            mock_settings.VIN_AUCTION_TIMEOUT_SECONDS = 45.0
            out = await lookup_vin_check("5N1AT2MV9JC767550")
        self.assertEqual(out.vendor, "Nissan")
        self.assertEqual(out.model, "Rogue")
        self.assertEqual(out.model_year, 2018)
        self.assertIsNotNone(out.auction)
        self.assertEqual(out.auction.primary_damage, "Front End")
        self.assertIn("Базі ДАІ", out.note or "")


if __name__ == "__main__":
    unittest.main()
