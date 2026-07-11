"""Unit tests for production secrets guard."""

from __future__ import annotations

import unittest

from app.core.secrets_guard import assert_production_secrets


class SecretsGuardTests(unittest.TestCase):
    def test_allows_debug(self):
        assert_production_secrets(
            debug=True,
            secret_key="change-me-in-production",
            internal_api_secret="change-me-internal",
            admin_password="admin123",
            frontend_url="https://carbit.info",
        )

    def test_allows_localhost(self):
        assert_production_secrets(
            debug=False,
            secret_key="change-me-in-production",
            internal_api_secret="change-me-internal",
            admin_password="admin123",
            frontend_url="http://localhost:3000",
        )

    def test_rejects_weak_production(self):
        with self.assertRaises(RuntimeError):
            assert_production_secrets(
                debug=False,
                secret_key="change-me-in-production",
                internal_api_secret="change-me-internal",
                admin_password="admin123",
                frontend_url="https://carbit.info",
            )

    def test_allows_strong_production(self):
        assert_production_secrets(
            debug=False,
            secret_key="a" * 32,
            internal_api_secret="b" * 24,
            admin_password="VeryStrongAdminPass1",
            frontend_url="https://carbit.info",
        )


if __name__ == "__main__":
    unittest.main()
