import unittest

from app.services.listings.seller_contact import (
    enrich_listing_seller_contact,
    extract_phone_from_text,
    extract_telegram_from_text,
    is_usable_phone,
    normalize_phone,
    seller_contact_from_auto_ria,
    seller_contact_from_imperiya,
    seller_contact_from_telegram,
)


class SellerContactTests(unittest.TestCase):
    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("067 123 45 67"), "+380671234567")
        self.assertEqual(normalize_phone("+380671234567"), "+380671234567")

    def test_rejects_masked_auto_ria_phone(self):
        self.assertFalse(is_usable_phone("(0XX) XXX XX XX"))
        contact = seller_contact_from_auto_ria(
            {
                "dealer": {"name": "Автосалон X", "link": "/dealers/avtosalon-x/"},
                "userPhoneData": {"phone": "(0XX) XXX XX XX"},
            }
        )
        self.assertIsNone(contact["seller_phone"])
        self.assertEqual(contact["seller_name"], "Автосалон X")
        self.assertTrue(contact["seller_url"].endswith("/dealers/avtosalon-x/"))

    def test_telegram_contact(self):
        contact = seller_contact_from_telegram(
            phone="0671234567",
            contact_username="KT1255E",
            description="Дзвоніть 0671234567 @KT1255E",
        )
        self.assertEqual(contact["seller_phone"], "+380671234567")
        self.assertEqual(contact["seller_telegram"], "KT1255E")

    def test_extract_from_description(self):
        self.assertEqual(extract_phone_from_text("Тел. 0 97 555 44 33"), "+380975554433")
        self.assertEqual(extract_telegram_from_text("Пишіть t.me/seller_auto"), "seller_auto")

    def test_imperiya_dealer(self):
        contact = seller_contact_from_imperiya(
            {
                "dealer": {"name": "Стиль-Авто", "slug": "styl-avto"},
                "contact": {"name": "Олег"},
            }
        )
        self.assertEqual(contact["seller_name"], "Стиль-Авто")
        self.assertEqual(contact["seller_url"], "https://imperiya-auto.com.ua/dealer/styl-avto")

    def test_enrich_from_description_for_legacy_listing(self):
        from app.schemas.schemas import ListingOut
        from app.core.timezone import now_kyiv

        now = now_kyiv()
        listing = ListingOut(
            id="telegram_test_1",
            source="telegram",
            title="Test",
            brand="Toyota",
            model="Camry",
            year=2018,
            price=10000,
            currency="USD",
            mileage=100000,
            fuel="Бензин",
            transmission="Автомат",
            region="Київ",
            description="Продам Toyota. 0671112233 @car_seller",
            images=[],
            url="https://t.me/test/1",
            seller_type="private",
            price_history=[],
            is_duplicate=False,
            published_at=now,
            found_at=now,
        )
        enriched = enrich_listing_seller_contact(listing)
        self.assertEqual(enriched.seller_phone, "+380671112233")
        self.assertEqual(enriched.seller_telegram, "car_seller")


if __name__ == "__main__":
    unittest.main()
