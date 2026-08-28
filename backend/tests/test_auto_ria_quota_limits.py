from __future__ import annotations

import unittest

from app.services.auto_ria.quota_limits import resolve_auto_ria_quota_limits


class AutoRiaQuotaLimitsTests(unittest.TestCase):
    def test_free_package(self):
        self.assertEqual(resolve_auto_ria_quota_limits("free", 0, 0), (1_000, 30, "free"))

    def test_explicit_overrides_when_no_package(self):
        self.assertEqual(resolve_auto_ria_quota_limits("", 50_000, 500), (50_000, 500, None))

    def test_package_overrides_explicit_quotas(self):
        self.assertEqual(resolve_auto_ria_quota_limits("1m", 1000, 30), (1_000_000, 20_000, "1m"))


if __name__ == "__main__":
    unittest.main()
