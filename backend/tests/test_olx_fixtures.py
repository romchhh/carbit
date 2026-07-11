from __future__ import annotations

from pathlib import Path

from app.services.olx.parser import parse_listing_page

FIXTURE = Path(__file__).parent / "fixtures" / "olx" / "search_page.html"


def test_olx_fixture_next_data_and_cards():
    html = FIXTURE.read_text(encoding="utf-8")
    listings = parse_listing_page(html)
    ids = {item.listing_id for item in listings if item.listing_id}
    assert "424242" in ids
    # Card fallback may also appear
    assert any("BMW" in (item.title or "") for item in listings) or any(
        "VW" in (item.title or "") for item in listings
    )
