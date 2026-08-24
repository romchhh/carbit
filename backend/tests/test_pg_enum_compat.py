"""PostgreSQL compatibility: ORM enums must not emit native PG ENUM casts."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import insert

from app.models.models import (
    BillingSubscription,
    Listing,
    MonitoringSourceRequest,
    Notification,
    NotificationType,
    ParseRun,
    ParseRunStatus,
    PlanTier,
    Source,
    SourceRequestStatus,
    SubscriptionStatus,
    User,
)


def _compile(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


class PgEnumCompatTests(unittest.TestCase):
    def test_str_enum_columns_disable_native_pg_enum(self):
        for table in (
            User.__table__,
            Listing.__table__,
            Notification.__table__,
            ParseRun.__table__,
            MonitoringSourceRequest.__table__,
            BillingSubscription.__table__,
        ):
            for column in table.columns:
                if not hasattr(column.type, "native_enum"):
                    continue
                self.assertFalse(
                    column.type.native_enum,
                    f"{table.name}.{column.name} must use native_enum=False",
                )

    def test_listing_insert_sql_has_no_source_enum_cast(self):
        now = datetime.now(timezone.utc)
        stmt = insert(Listing).values(
            id="test_listing_1",
            external_id="1",
            source=Source.auto_ria,
            title="Test",
            brand="BMW",
            model="X5",
            year=2020,
            price=10000,
            currency="USD",
            mileage=1000,
            fuel="Бензин",
            transmission="Автомат",
            region="Київ",
            images=[],
            url="https://example.com",
            seller_type="private",
            price_history=[],
            is_duplicate=False,
            published_at=now,
            found_at=now,
        )
        sql = _compile(stmt)
        self.assertNotIn("::source", sql.lower())

    def test_user_insert_sql_has_no_plantier_enum_cast(self):
        now = datetime.now(timezone.utc)
        stmt = insert(User).values(
            id="user_test_1",
            email="test@example.com",
            name="Test",
            plan=PlanTier.free,
            created_at=now,
        )
        sql = _compile(stmt)
        self.assertNotIn("::plantier", sql.lower())

    def test_notification_insert_sql_has_no_notificationtype_cast(self):
        now = datetime.now(timezone.utc)
        stmt = insert(Notification).values(
            id="notif_1",
            user_id="user_1",
            type=NotificationType.system,
            title="t",
            body="b",
            created_at=now,
        )
        sql = _compile(stmt)
        self.assertNotIn("::notificationtype", sql.lower())

    def test_parse_run_insert_sql_has_no_parserunstatus_cast(self):
        now = datetime.now(timezone.utc)
        stmt = insert(ParseRun).values(
            id="run_1",
            status=ParseRunStatus.running,
            triggered_by="test",
            filter_groups=0,
            searches_processed=0,
            listings_found=0,
            listings_new=0,
            notifications_sent=0,
            log=[],
            started_at=now,
        )
        sql = _compile(stmt)
        self.assertNotIn("::parserunstatus", sql.lower())

    def test_source_enum_includes_all_search_sources(self):
        values = {member.value for member in Source}
        for required in ("auto_ria", "olx", "telegram", "imperiya", "udrive"):
            self.assertIn(required, values)


if __name__ == "__main__":
    unittest.main()
