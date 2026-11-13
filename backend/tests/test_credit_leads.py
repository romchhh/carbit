"""Tests for credit lead API."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

_VALID_PAYLOAD = {
    "name": "Тест Тестовий",
    "phone": "380501112233",
    "listing_id": "olx_test_1",
    "listing_title": "Audi A4 2018",
    "listing_url": "https://carbit.info/app/listing/olx_test_1",
    "car_price_uah": 400_000,
    "down_payment_percent": 20,
    "term_months": 36,
    "loan_amount_uah": 320_000,
    "monthly_payment_uah": 15_000,
    "registration_mode": "with_registration",
    "nominal_rate_percent": 0.01,
    "real_annual_rate_percent": 12.5,
    "one_time_fee_uah": 9440,
    "notary_fee_uah": 0,
    "total_repayment_uah": 540_000,
}


class CreditLeadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_credit_lead_requires_valid_phone(self):
        res = self.client.post(
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
        self.assertEqual(res.status_code, 422)

    def test_credit_lead_sends_email_and_telegram(self):
        with (
            patch(
                "app.api.v1.credit_leads.send_credit_lead_email",
                new_callable=AsyncMock,
            ) as send_email,
            patch(
                "app.api.v1.credit_leads.notify_monitor_admins",
                new_callable=AsyncMock,
            ) as notify_admins,
            patch(
                "app.api.v1.credit_leads.CREDIT_LEAD_EMAILS",
                (
                    "Урдей Іван Остапович <Ivan.Urdei@bisbank.com.ua>",
                    "romanbiznesssmen@gmail.com",
                    "zond.agency@gmail.com",
                ),
            ),
        ):
            res = self.client.post("/api/v1/credit-leads", json=_VALID_PAYLOAD)

        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["ok"])
        send_email.assert_awaited_once()
        kwargs = send_email.await_args.kwargs
        self.assertEqual(
            kwargs["to"],
            [
                "Урдей Іван Остапович <Ivan.Urdei@bisbank.com.ua>",
                "romanbiznesssmen@gmail.com",
                "zond.agency@gmail.com",
            ],
        )
        self.assertIn("Тест Тестовий", kwargs["subject"])
        self.assertTrue(any(label == "Телефон" for label, _ in kwargs["rows"]))
        notify_admins.assert_awaited_once()

    def test_credit_lead_fails_when_email_fails(self):
        with (
            patch(
                "app.api.v1.credit_leads.send_credit_lead_email",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Failed to send email"),
            ),
            patch(
                "app.api.v1.credit_leads.notify_monitor_admins",
                new_callable=AsyncMock,
            ) as notify_admins,
            patch(
                "app.api.v1.credit_leads.CREDIT_LEAD_EMAILS",
                ("Ivan.Urdei@bisbank.com.ua",),
            ),
        ):
            res = self.client.post("/api/v1/credit-leads", json=_VALID_PAYLOAD)

        self.assertEqual(res.status_code, 503)
        notify_admins.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
