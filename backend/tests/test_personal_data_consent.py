"""Registration requires Bisbank personal-data / BKI consent."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class PersonalDataConsentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_register_send_code_requires_consent(self):
        with patch(
            "app.api.v1.auth.get_verified_phone_user",
            new_callable=AsyncMock,
            return_value=None,
        ):
            res = self.client.post(
                "/api/v1/auth/phone/send-code",
                json={
                    "phone": "380501112233",
                    "intent": "register",
                    "name": "Тест",
                    "personal_data_consent": False,
                },
            )
        self.assertEqual(res.status_code, 400)
        self.assertIn("згода", res.json()["detail"].lower())

    def test_login_send_code_does_not_require_consent(self):
        fake_user = object()
        with (
            patch(
                "app.api.v1.auth.get_verified_phone_user",
                new_callable=AsyncMock,
                return_value=fake_user,
            ),
            patch(
                "app.api.v1.auth.phone_verify_svc.phone_auth_resend_allowed",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.auth.phone_verify_svc.store_phone_auth",
                new_callable=AsyncMock,
                return_value="123456",
            ),
            patch(
                "app.api.v1.auth.deliver_phone_auth_code",
                new_callable=AsyncMock,
                return_value=("ok", "sms"),
            ),
            patch(
                "app.api.v1.auth.phone_verify_svc.update_phone_auth_meta",
                new_callable=AsyncMock,
            ),
            patch("app.api.v1.auth.enforce_rate_limit", new_callable=AsyncMock),
        ):
            res = self.client.post(
                "/api/v1/auth/phone/send-code",
                json={
                    "phone": "380501112233",
                    "intent": "login",
                    "personal_data_consent": False,
                },
            )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
