from __future__ import annotations

import json

from app.services.olx.parser import (
    OlxListing,
    OlxSearchParams,
    _listing_from_embedded,
    _listing_mileage_km,
    _parse_mileage_text,
    _parse_single_card,
    build_search_url,
    parse_listing_page,
    passes_olx_filters,
)


def test_build_search_url_newest_sort():
    url = build_search_url(OlxSearchParams(city_query="kyiv"))
    assert "search%5Border%5D=created_at%3Adesc" in url
    assert "currency=UAH" in url
    assert "/q-kyiv/" in url


def test_build_search_url_pagination():
    url = build_search_url(OlxSearchParams(brand="toyota", model="camry"), page=2)
    assert "page=2" in url
    assert "search%5Border%5D=created_at%3Adesc" in url


def test_parse_mileage_text_thousands():
    assert _parse_mileage_text("2018 · 120 тис. км") == "120 тис.км"


def test_parse_mileage_text_full_km():
    assert _parse_mileage_text("пробіг 118000 км") == "118000 км"


def test_listing_mileage_km_from_full_km():
    listing = OlxListing(mileage="118000 км")
    assert _listing_mileage_km(listing) == 118000


def test_embedded_listing_enrichment():
    raw = {
        "id": 123456,
        "url": "/d/uk/obyavlenie/toyota-camry-IDabc123.html",
        "title": "Toyota Camry 2018",
        "createdTime": "2026-03-01T10:00:00Z",
        "price": {"regularPrice": {"value": 14500, "currency": "USD"}},
        "location": {"city": {"name": "Київ"}},
        "params": [
            {"name": "Рік випуску", "value": "2018"},
            {"name": "Пробіг", "value": "95 тис. км"},
        ],
        "photos": [{"link": "https://ireland.apollo.olxcdn.com/v1/files/abc/image"}],
    }
    listing = _listing_from_embedded(raw)
    assert listing is not None
    assert listing.listing_id == "123456"
    assert listing.price == "14500"
    assert listing.currency == "USD"
    assert listing.year == "2018"
    assert listing.city == "Київ"
    assert listing.mileage == "95 тис. км"
    assert listing.photo_url


def test_parse_listing_page_from_next_data():
    payload = {
        "props": {
            "pageProps": {
                "ads": [
                    {
                        "id": 999,
                        "url": "/d/uk/obyavlenie/test-IDzzz.html",
                        "title": "Audi A4",
                        "price": {"regularPrice": {"value": 12000, "currency": "UAH"}},
                        "location": {"city": {"name": "Львів"}},
                    }
                ]
            }
        }
    }
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>'
    listings = parse_listing_page(html)
    assert len(listings) >= 1
    assert any(item.listing_id == "999" for item in listings)


def test_parse_card_html_mileage():
    html = """
    <div data-testid="l-card">
      <a href="/d/uk/obyavlenie/skoda-octavia-IDtest1.html">
        <h4>Skoda Octavia</h4>
        <p data-testid="ad-price">320 000 грн</p>
        <p data-testid="ad-params">2016 · 145000 км</p>
        <p data-testid="location-date">Київ - 2 години тому</p>
      </a>
    </div>
    """
    from bs4 import BeautifulSoup

    card = BeautifulSoup(html, "html.parser").select_one('[data-testid="l-card"]')
    listing = _parse_single_card(card)
    assert listing is not None
    assert listing.price == "320000"
    assert listing.currency == "UAH"
    assert listing.mileage == "145000 км"


def test_embedded_city_name_flat_location():
    raw = {
        "id": 777,
        "url": "/d/uk/obyavlenie/zeekr-001-IDabc.html",
        "title": "Zeekr 001 2024",
        "createdTime": "2026-07-01T10:00:00Z",
        "price": {"regularPrice": {"value": 34000, "currency": "USD"}},
        "location": {
            "cityName": "Київ",
            "regionName": "Київська область",
            "districtName": "Шевченківський",
            "pathName": "Київська область, Київ, Шевченківський",
        },
    }
    listing = _listing_from_embedded(raw)
    assert listing is not None
    assert listing.city == "Київ"


def test_passes_olx_filters_text_search_city_kyiv():
    listing = OlxListing(
        title="Zeekr 001 WE 2025",
        price="20500",
        currency="USD",
        city="Боярка",
        raw_params={
            "location": {
                "cityName": "Боярка",
                "regionName": "Київська область",
                "pathName": "Київська область, Боярка",
            }
        },
    )
    params = OlxSearchParams(
        text_query="Zeekr",
        brand_label="Zeekr",
        model_label="001",
        city_query="київська-область",
        currency="USD",
    )
    assert passes_olx_filters(listing, params)

    kyiv_only = OlxSearchParams(
        text_query="Zeekr",
        brand_label="Zeekr",
        model_label="001",
        city_query="kyiv",
        currency="USD",
    )
    assert not passes_olx_filters(listing, kyiv_only)


def test_passes_olx_filters_mileage_full_km():
    listing = OlxListing(
        title="VW Golf 2015",
        price="10000",
        currency="USD",
        year="2015",
        mileage="120000 км",
    )
    params = OlxSearchParams(mileage_from=100, mileage_to=150)
    assert passes_olx_filters(listing, params)