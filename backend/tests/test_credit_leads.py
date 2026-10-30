"""Tests for credit lead API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_credit_lead_requires_valid_phone():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/credit-leads",
            json={
                "name": "Тест",
                "phone": "123",
                "listing_title": "Audi A4",
                "car_price_uah": 400_000,
                "down_payment_percent": 20,
                "term_months": 36,
                "loan_amount_uah": 320_000,
                "monthly_payment_uah": 15_000,
            },
        )
    assert res.status_code == 422
