from __future__ import annotations

import unittest
from datetime import timedelta
from types import SimpleNamespace

from app.core.timezone import now_kyiv
from app.services.billing.plans import activate_plan, admin_access_days


class AdminAccessGrantTests(unittest.TestCase):
    def test_admin_access_days_year(self) -> None:
        self.assertEqual(admin_access_days(months=12), 365)
        self.assertEqual(admin_access_days(months=3), 90)
        self.assertEqual(admin_access_days(days=45), 45)

    def test_activate_extends_from_current_expiry(self) -> None:
        user = SimpleNamespace(
            plan=SimpleNamespace(value="lite"),
            plan_expires_at=now_kyiv() + timedelta(days=10),
        )
        activate_plan(user, "standard", access_days=30, extend_from_current=True)
        delta = user.plan_expires_at - now_kyiv()
        self.assertGreaterEqual(delta.days, 39)
        self.assertLessEqual(delta.days, 41)


if __name__ == "__main__":
    unittest.main()
