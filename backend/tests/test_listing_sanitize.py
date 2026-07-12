from __future__ import annotations

import unittest
from datetime import datetime

from app.core.timezone import KYIV_TZ
from app.schemas.schemas import ListingOut, PaginatedListings
from app.services.listings.sanitize import json_safe, sanitize_listing_out, sanitize_paginated_listings


def _listing(**overrides) -> ListingOut:
    base = dict(
        id="auto_ria_1",
        source="auto_ria",
        title="Audi A4",
        brand="Audi",
        model="A4",
        year=2015,
        price=12_500,
        currency="USD",
        mileage=200_000,
        fuel="Бензин",
        transmission="Автомат",
        region="Київ",
        description=None,
        images=["https://example.com/a.jpg", None, 123, "https://example.com/b.jpg"],
        url="https://auto.ria.com/x",
        seller_type="private",
        source_data={
            "USD": 12_500,
            "bad": float("nan"),
            "nested": {"ok": 1, "inf": float("inf")},
            "_fotos": {"huge": True},
        },
        price_history=[{"price": 1}, "nope", {"price": 2}],
        is_duplicate=False,
        published_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
        found_at=datetime(2026, 7, 1, tzinfo=KYIV_TZ),
    )
    base.update(overrides)
    # Construct via model_construct to allow dirty input then sanitize
    return ListingOut.model_construct(**base)


class ListingSanitizeTests(unittest.TestCase):
    def test_json_safe_drops_nan_and_fotos(self):
        raw = {"USD": 1, "x": float("nan"), "_fotos": {"a": 1}, "t": datetime(2026, 1, 1, tzinfo=KYIV_TZ)}
        clean = json_safe(raw)
        self.assertEqual(clean["USD"], 1)
        self.assertIsNone(clean["x"])
        self.assertNotIn("_fotos", clean)
        self.assertIsInstance(clean["t"], str)

    def test_sanitize_listing_coerces_images_and_history(self):
        item = sanitize_listing_out(_listing())
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.images, ["https://example.com/a.jpg", "https://example.com/b.jpg"])
        self.assertEqual(item.price_history, [{"price": 1}, {"price": 2}])
        self.assertNotIn("_fotos", item.source_data or {})
        # NaN removed
        self.assertIsNone((item.source_data or {}).get("bad"))

    def test_sanitize_paginated(self):
        page = sanitize_paginated_listings(
            PaginatedListings(items=[_listing()], total=1, page=1, per_page=20, pages=1)
        )
        self.assertEqual(len(page.items), 1)
        # Ensure FastAPI-like dump works
        page.model_dump(mode="json")


if __name__ == "__main__":
    unittest.main()
