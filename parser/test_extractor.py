#!/usr/bin/env python3
"""Офлайн-тести екстрактора (без Telegram)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from parser.extractor import (
    extract_car_data,
    is_car_search_request,
    is_valid_car_listing,
    normalize_listing_text,
)
from parser.models import CarListing


def _extract(text: str) -> CarListing:
    return extract_car_data(
        raw_text=text,
        channel="@test",
        message_id=1,
        group_message_ids=[1],
        source_link="https://t.me/test/1",
        posted_at=datetime.now(timezone.utc),
        photos=[],
    )


class ExtractorTests(unittest.TestCase):
    def test_normalize_markdown(self):
        raw = "**BMW X5** 2018 [деталі](https://t.me/x)"
        self.assertEqual(normalize_listing_text(raw), "BMW X5 2018 деталі")

    def test_bmw_cyrillic(self):
        listing = _extract("Продаю бмв x5 2018 рік, 3.0 дизель, 120 тис. км, 18500$")
        self.assertEqual(listing.brand, "BMW")
        self.assertEqual(listing.year, 2018)
        self.assertEqual(listing.price_amount, 18500)
        self.assertEqual(listing.price_currency, "USD")
        self.assertGreaterEqual(listing.confidence, 0.6)

    def test_mmr_price(self):
        listing = _extract("Jaguar F-PACE 2017\nMMR: $7,350\nПробіг: 98 тис. км")
        self.assertEqual(listing.brand, "Jaguar")
        self.assertEqual(listing.price_amount, 7350)
        self.assertEqual(listing.price_currency, "USD")

    def test_usd_without_symbol_import_channel(self):
        listing = _extract("Skoda Octavia 2012 рік, ціна 7300, пробіг 118 тис км")
        self.assertEqual(listing.price_currency, "USD")

    def test_uah_price(self):
        listing = _extract("Audi A4 2016, ціна 650 000 грн, Київ")
        self.assertEqual(listing.brand, "Audi")
        self.assertEqual(listing.price_amount, 650000)
        self.assertEqual(listing.price_currency, "UAH")

    def test_mercedes_nbsp_price(self):
        listing = _extract("Mercedes-Benz GLC-Class Coupe 2021\n💰 47\u00a0500\u00a0$\n📏 60 тис. км")
        self.assertEqual(listing.year, 2021)
        self.assertEqual(listing.price_amount, 47500)
        self.assertEqual(listing.price_currency, "USD")

    def test_man_not_in_roman(self):
        listing = _extract("Roman продам авто без посередників, 2015 рік, 12000$")
        self.assertNotEqual(listing.brand, "MAN")

    def test_webinar_without_car_fields_not_listing(self):
        text = "Вебінар 15 липня: як продавати авто в 2026 році. Підпишись на канал!"
        listing = _extract(text)
        self.assertFalse(is_valid_car_listing(listing))

    def test_valid_listing(self):
        listing = _extract("Mercedes E220 2019, 25000$, не бита, Одеса")
        self.assertTrue(is_valid_car_listing(listing))

    def test_empty_photo_only(self):
        listing = _extract("")
        self.assertFalse(is_valid_car_listing(listing))

    def test_buyer_search_request_bmw_list(self):
        text = """#Пошук авто🕵️

BMW от 2020 г.в.:
X5M F95 - до 65$
X5M50i - до 55$
X5 G05 (LCI) 3.0 - 60$
X5 G05 (дорест) 3.0 в М-пак - 40$
M8 F92/93 - до 65$
M5 F90 (рест) - до 65$
X6 также рассмотрю

✍️ @nik_6699"""
        self.assertTrue(is_car_search_request(text))
        listing = _extract(text)
        self.assertFalse(is_valid_car_listing(listing))

    def test_sale_listing_not_search_request(self):
        text = "Продаю BMW X5 2021, пробіг 45 тис, 52000$"
        self.assertFalse(is_car_search_request(text))
        listing = _extract(text)
        self.assertTrue(is_valid_car_listing(listing))

    def test_hashtags_stripped(self):
        listing = _extract("#авто #продам Toyota Camry 2017, 14500$")
        self.assertEqual(listing.brand, "Toyota")
        self.assertEqual(listing.year, 2017)

    def test_hashtags_keep_brand_and_vin(self):
        raw = """#Zeekr #001 Facelift

Zeekr 001 Facelift
2024 рік
13к пробіг
електро
Повний привід

📍 м. Київ

#L6T79ZCE4RP134189

💰47.000$💰45.000$
✍️ @KT1255E
"""
        listing = _extract(raw)
        self.assertEqual(listing.brand, "Zeekr")
        self.assertIn("001", listing.model or "")
        self.assertEqual(listing.year, 2024)
        self.assertEqual(listing.mileage_km, 13000)
        self.assertEqual(listing.fuel_type, "electric")
        self.assertEqual(listing.drive_type, "awd")
        self.assertEqual(listing.location_city, "Київ")
        self.assertEqual(listing.price_amount, 45000)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.condition_flags.get("vin"), "L6T79ZCE4RP134189")
        self.assertEqual(listing.contact_username, "KT1255E")
        self.assertNotEqual(listing.condition_flags.get("vin"), "FACELFTZEEKR001FA")

    def test_mileage_short_k(self):
        listing = _extract("BMW X5 2019\n85к пробіг\n22000$")
        self.assertEqual(listing.mileage_km, 85000)

    def test_year_with_cyrillic_g_suffix(self):
        listing = _extract(
            "MAZDA MX-30 2021г. Электро 35,5 kWt 45 тыс.км. Автомат. "
            "Без ДТП, все в оригинале. Запас хода 220 км. 14900$. 067-7960229"
        )
        self.assertEqual(listing.brand, "Mazda")
        self.assertEqual(listing.year, 2021)
        self.assertEqual(listing.model, "MX-30")
        self.assertEqual(listing.price_amount, 14900)
        self.assertEqual(listing.mileage_km, 45000)

    def test_year_rik_suffix(self):
        listing = _extract("Toyota Camry 2019 рік, 14500$")
        self.assertEqual(listing.year, 2019)
        self.assertEqual(listing.model, "Camry")

    def test_mileage_label(self):
        listing = _extract("Volkswagen Passat 2015\nПробіг: 145 тис. км\nЦіна: 9800$")
        self.assertEqual(listing.brand, "Volkswagen")
        self.assertEqual(listing.mileage_km, 145000)
        self.assertEqual(listing.price_amount, 9800)

    def test_full_km_mileage(self):
        listing = _extract("Ford Focus 2014, пробіг 118000 км, 7500$")
        self.assertEqual(listing.mileage_km, 118000)

    def test_phone_not_price(self):
        listing = _extract("Продам авто, тел 0671234567, 2016 рік")
        self.assertNotEqual(listing.price_amount, 671234567)

    def test_vin_flag(self):
        listing = _extract("BMW 320 2016, VIN WBA8E9G50JNU12345, 12000$")
        self.assertEqual(listing.condition_flags.get("vin"), "WBA8E9G50JNU12345")

    def test_vin_from_plain_line(self):
        text = """
Mercedes-Benz G63 2023
269500$
W1NWH5AB1SX014976
"""
        listing = _extract(text)
        self.assertEqual(listing.condition_flags.get("vin"), "W1NWH5AB1SX014976")

    def test_vin_not_blocked_by_later_letter_i(self):
        listing = _extract("Toyota Camry 2018 9000$\nWBA8E9G50JNU12345\nOfficial import")
        self.assertEqual(listing.condition_flags.get("vin"), "WBA8E9G50JNU12345")

    def test_ford_fusion_arrival_date_not_model_year(self):
        text = """📍Прибула в Одесу — 19.07.2026

🔥 Ford Fusion SE 2020

✔️ Двигун 1.5 л ✔️ Пробіг — 140 000 км ✔️ Авто заводиться та їде

💰 Ціна з доставкою та розмитненням — 7800$

098-904-36-87"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Ford")
        self.assertEqual(listing.year, 2020)
        self.assertEqual(listing.price_amount, 7800)
        self.assertEqual(listing.mileage_km, 140000)
        self.assertEqual(listing.location_city, "Одеса")
        self.assertTrue(is_valid_car_listing(listing))

    def test_mini_countryman_not_bmw_from_service_name(self):
        """Сервіс «Zolotoy BMW Garage» у тілі не повинен перебивати MINI із заголовка."""
        text = """MINI COUNTRYMAN S 2013
Повний привід спорт комплектація автомат
$10500
VIN номер: WMWZC5C52DWP34187

Продаю власне авто. Обслуговувались на Zolotoy BMW Garage та Cooper Centre.
Авто повної комплектації: 1.6 турбований повний привід.
Рідний пробіг 149 тисяч.
Київ"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Mini")
        self.assertIsNotNone(listing.model)
        self.assertIn("countryman", (listing.model or "").lower())
        self.assertEqual(listing.year, 2013)
        self.assertEqual(listing.price_amount, 10500)
        self.assertEqual(listing.mileage_km, 149000)
        self.assertTrue(is_valid_car_listing(listing))

    def test_service_name_before_mini_still_picks_car(self):
        """Навіть якщо «BMW Garage» згадано раніше за Mini у тексті — беремо авто."""
        text = (
            "Обслуговування: Zolotoy BMW Garage\n"
            "MINI COUNTRYMAN S 2014\n"
            "$9800 пробіг 120 тис. км Київ"
        )
        listing = _extract(text)
        self.assertEqual(listing.brand, "Mini")
        self.assertIn("countryman", (listing.model or "").lower())

    def test_countryman_without_mini_brand(self):
        """Лише Countryman у заголовку → Mini Countryman."""
        text = "Countryman S 2015\n$8500\nпробіг 130 тис км, Київ"
        listing = _extract(text)
        self.assertEqual(listing.brand, "Mini")
        self.assertIn("Countryman", listing.model or "")

    def test_salon_labeled_audi_q5(self):
        """Формат салону: Марка/Модель/Ціна/Пробіг/Рік/Двигун + VIN + США."""
        text = """🔴 Марка: Audi | Модель: Q5 |
Ціна: 37900 $ | Пробіг: 23000 | Рік: 2023

Двигун: 2.0 | Паливо: Бензин | Коробка: Автомат | Привід: Повний |
Тип авто: Позашляховик / Кросовер |

📦 Авто в наявності в салоні
#Київ Автосалон «Імперія Авто»

WA1EAAFY1R2037060
Авто пригнане з США
+38 0990317664 Олексій
#Audi
#від_30000_до_40000$
"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Audi")
        self.assertEqual(listing.model, "Q5")
        self.assertEqual(listing.year, 2023)
        self.assertEqual(listing.price_amount, 37900)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.mileage_km, 23000)
        self.assertEqual(listing.engine_volume_l, 2.0)
        self.assertEqual(listing.fuel_type, "petrol")
        self.assertEqual(listing.transmission, "automatic")
        self.assertEqual(listing.drive_type, "awd")
        self.assertEqual(listing.location_city, "Київ")
        self.assertEqual((listing.condition_flags or {}).get("vin"), "WA1EAAFY1R2037060")
        self.assertTrue(is_valid_car_listing(listing))

    def test_mileage_plain_five_digits(self):
        listing = _extract("BMW X5 2020, ціна 25000$, Пробіг: 45000, Київ")
        self.assertEqual(listing.mileage_km, 45000)

    def test_uah_typo_with_vin_treated_as_usd(self):
        """«17800₴» при VIN — типова помилка символу валюти → USD."""
        text = """Volkswagen Touareg
Рік - 2014
3,0 дизель
АКПП
Повний привід
Пробіг 231 тис км
Vin: WVGEP9BP9ED013812
Місто Бориспіль
Ціна 17800₴
☎️ 0686654727"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Volkswagen")
        self.assertEqual(listing.model, "Touareg")
        self.assertEqual(listing.year, 2014)
        self.assertEqual(listing.price_amount, 17800)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.mileage_km, 231000)
        self.assertEqual(listing.engine_volume_l, 3.0)
        self.assertEqual(listing.fuel_type, "diesel")
        self.assertEqual((listing.condition_flags or {}).get("vin"), "WVGEP9BP9ED013812")
        self.assertTrue(is_valid_car_listing(listing))

    def test_real_uah_price_still_uah(self):
        listing = _extract("Audi A4 2016, ціна 650 000 грн, Київ")
        self.assertEqual(listing.price_currency, "UAH")

    def test_salon_nissan_qashqai_with_business_ad_footer(self):
        """Футер «Реклама бізнесу» не відсікає реальне оголошення салону."""
        text = """🔴 Марка: Nissan | Модель: Qashqai |
Ціна: 18200 $ | Пробіг: 164000 | Рік: 2018

Двигун: 1.6 | Паливо: Дизель | Коробка: Автомат | Привід: Передній |
Тип авто: Позашляховик / Кросовер |

📦 Авто в наявності в салоні
#Київ Автосалон «Імперія Авто»
SJNFDAJ11U2746847
📞 Контакти:
+38 0675760057 Андрій
#Nissan
📢 Реклама бізнесу
💰 Авто в лізинг / кредит"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Nissan")
        self.assertEqual(listing.model, "Qashqai")
        self.assertEqual(listing.year, 2018)
        self.assertEqual(listing.price_amount, 18200)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.mileage_km, 164000)
        self.assertEqual(listing.engine_volume_l, 1.6)
        self.assertEqual(listing.fuel_type, "diesel")
        self.assertEqual(listing.transmission, "automatic")
        self.assertEqual(listing.drive_type, "fwd")
        self.assertEqual((listing.condition_flags or {}).get("vin"), "SJNFDAJ11U2746847")
        self.assertTrue(is_valid_car_listing(listing))

    def test_kia_rio_emoji_card(self):
        text = """🚗: Kia Rio
📆Рік: 2012
🏃Пробіг: 199 тис. км
⚙️Двигун: Бензин 1.4л
🕹Коробка Передач: Механічна
🛞Привід: Передній
💸Ціна: 8800$
🇺🇦Місто: Сумська обл., Кролевець
📱Телефон: 066 330 4631"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Kia")
        self.assertEqual(listing.model, "Rio")
        self.assertEqual(listing.year, 2012)
        self.assertEqual(listing.mileage_km, 199000)
        self.assertEqual(listing.engine_volume_l, 1.4)
        self.assertEqual(listing.fuel_type, "petrol")
        self.assertEqual(listing.transmission, "manual")
        self.assertEqual(listing.drive_type, "fwd")
        self.assertEqual(listing.price_amount, 8800)
        self.assertEqual(listing.location_city, "Кролевець")
        self.assertTrue(is_valid_car_listing(listing))

    def test_renault_kangoo_full_km_mileage(self):
        text = (
            "Renault Kangoo Maxi 12.2021р.випуску, пригнаний з Бельгії 06.2026р, "
            "розмитнений-100%+сертифікат, авто в гарному стані, "
            "пройшов ТО в Бельгії на пробігі 96263км , 22.10.25. "
            "без ДТП, можливо установка кондиціонера +$ -12500$ Дніпро 0958431995"
        )
        listing = _extract(text)
        self.assertEqual(listing.brand, "Renault")
        self.assertIn("Kangoo", listing.model or "")
        self.assertEqual(listing.year, 2021)
        self.assertEqual(listing.mileage_km, 96263)
        self.assertEqual(listing.price_amount, 12500)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.location_city, "Дніпро")
        self.assertTrue((listing.condition_flags or {}).get("not_damaged"))
        self.assertTrue((listing.condition_flags or {}).get("customs_cleared"))
        self.assertTrue(is_valid_car_listing(listing))

    def test_not_search_request_potrebuye_avto(self):
        """«Вкладень не потребує Авто» — продаж, не запит «є авто?»."""
        text = (
            "Golf VII 2013рік\n1.2 бензин\nВкладень не потребує\n"
            "Авто від власника\n💰7800$"
        )
        self.assertFalse(is_car_search_request(text))

    def test_hyundai_kona_40kw(self):
        text = (
            "Hyundai Kona 40kw, 2020р, пригнана з Німеччини 12.2025, "
            "вже на Українській регістрації, перша регистрація 2021р, "
            "пройшов ТО в Німеччині 07.2025р. -18800$ Дніпро 0958431995"
        )
        listing = _extract(text)
        self.assertEqual(listing.brand, "Hyundai")
        self.assertEqual(listing.model, "Kona")
        self.assertEqual(listing.year, 2020)
        self.assertEqual(listing.price_amount, 18800)
        self.assertEqual(listing.fuel_type, "electric")
        self.assertEqual(listing.location_city, "Дніпро")
        self.assertTrue(is_valid_car_listing(listing))

    def test_golf_vii_without_vw_brand(self):
        text = """🚘
Golf VII 2013рік 
1.2 бензин
Авто доглянуте,без гнилі,без рижиків
Вкладень не потребує 
Авто від власника
☎️0964666184
💰7800$"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Volkswagen")
        self.assertIn("Golf", listing.model or "")
        self.assertIn("VII", listing.model or "")
        self.assertEqual(listing.year, 2013)
        self.assertEqual(listing.price_amount, 7800)
        self.assertEqual(listing.engine_volume_l, 1.2)
        self.assertEqual(listing.fuel_type, "petrol")
        self.assertFalse(is_car_search_request(text))
        self.assertTrue(is_valid_car_listing(listing))

    def test_skoda_octavia_a7_price_emoji(self):
        text = """Skoda Octavia A7 2013 1.4 TSI•
Коробка Механіка бст
Привід передній
придбана з салону( 1 власник)
Авто в Києві
9600💵
0673215050"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Skoda")
        self.assertIn("Octavia", listing.model or "")
        self.assertEqual(listing.year, 2013)
        self.assertEqual(listing.price_amount, 9600)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.engine_volume_l, 1.4)
        self.assertEqual(listing.transmission, "manual")
        self.assertEqual(listing.drive_type, "fwd")
        self.assertEqual(listing.location_city, "Київ")
        self.assertTrue(is_valid_car_listing(listing))

    def test_renault_megan_typo_mileage_t_km(self):
        """«Megan» + «253т. км» + emoji-рядки."""
        text = """🚐 Renault Megan 3 
📆 Рік - 2012
🛣️ Пробіг - 253т. км
🛢 Паливо - дизель
🕹️ Механіка, передній привід
💵 $9600
🌏 Київ
📱 Тел. 0665940968

Авто з-за кордону — це не реклама салону"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Renault")
        self.assertIn("Megan", listing.model or "")
        self.assertEqual(listing.year, 2012)
        self.assertEqual(listing.price_amount, 9600)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.mileage_km, 253000)
        self.assertEqual(listing.fuel_type, "diesel")
        self.assertEqual(listing.transmission, "manual")
        self.assertEqual(listing.drive_type, "fwd")
        self.assertEqual(listing.location_city, "Київ")
        self.assertTrue(is_valid_car_listing(listing))

    def test_volvo_s80_benz_turbo(self):
        text = """🛞Volvo s80 II🛞
       2006рік.
🔥2.5 Т, бенз🔥
АКПП (aisin 6-ст) 

  пробіг: 180тис🎁

Перша  офіційна Volvo s80 II, куплена у дилера в Одесі! 

Літня шини Continental 2025 рік.

Автомобіль вартий вашої уваги, навіть аварійне колесо рідне

💰Ціна: 8850$ 🍯
Одеська обл., м.Біляївка
0969712307-Ivan"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Volvo")
        self.assertIn("s80", (listing.model or "").lower())
        self.assertEqual(listing.year, 2006)
        self.assertEqual(listing.price_amount, 8850)
        self.assertEqual(listing.mileage_km, 180000)
        self.assertEqual(listing.engine_volume_l, 2.5)
        self.assertEqual(listing.fuel_type, "petrol")
        self.assertEqual(listing.transmission, "automatic")
        self.assertEqual(listing.location_city, "Біляївка")
        self.assertTrue(is_valid_car_listing(listing))

    def test_land_rover_discovery_sport_import(self):
        text = """🚗LAND ROVER DISCOVERY SPORT S.

2024. 2.0. 14т.миль.
VIN - SALCJ2FX3RH351759.

Машина реальна (не реклама), доступна до продажу ! Куплена в Америці. Пливе в Литву (порт Клайпеда). Звідти автовозом доставляємо в Україну.

🔜Судозахід в Литву- 29.08.2026.

💰26500$ – ціна під ключ на Українському обліку (без ремонту).

Авто повністю на ходу (Run and Drive).
Має незначне пошкодження заднього правого колеса. Ремонт мінімальний!

Можливий безготівковий розрахунок!

➡️TG: @dmytro_cantora
🗣️Дані для контакту: +380933002003"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Land Rover")
        self.assertIn("sport", (listing.model or "").lower())
        self.assertEqual(listing.year, 2024)
        self.assertEqual(listing.price_amount, 26500)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.engine_volume_l, 2.0)
        self.assertIsNotNone(listing.mileage_km)
        self.assertAlmostEqual(listing.mileage_km, 14000 * 1.60934, delta=50)
        self.assertEqual((listing.condition_flags or {}).get("vin"), "SALCJ2FX3RH351759")
        self.assertTrue(is_valid_car_listing(listing))

    def test_ford_focus_auction_autopark(self):
        text = """Ford Focus - 2014
🔥Стартова ціна: 3000$
💵Ринкова ціна: 4990$

Пригнано з Європи 🇪🇺

💥 В середу 10:00–19:00 лот буде доступний на Autopark.ua
👉 Для участі в АУКЦІОНІ переходь на сайт

🛣 Пробіг: 210 тис. км
⛽️ Паливо: Бензин
⚙️ Об‘єм двигуна: 1.0
🔻 Привід: Передній
🕹 КПП: Механіка
📍 Місто: Львів"""
        listing = _extract(text)
        self.assertEqual(listing.brand, "Ford")
        self.assertEqual(listing.model, "Focus")
        self.assertEqual(listing.year, 2014)
        self.assertEqual(listing.price_amount, 4990)
        self.assertEqual(listing.price_currency, "USD")
        self.assertEqual(listing.mileage_km, 210000)
        self.assertEqual(listing.engine_volume_l, 1.0)
        self.assertEqual(listing.fuel_type, "petrol")
        self.assertEqual(listing.transmission, "manual")
        self.assertEqual(listing.drive_type, "fwd")
        self.assertEqual(listing.location_city, "Львів")
        self.assertTrue(is_valid_car_listing(listing))


if __name__ == "__main__":
    unittest.main()
