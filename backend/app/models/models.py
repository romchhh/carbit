import uuid
from datetime import datetime, timedelta

from sqlalchemy import String, Boolean, DateTime, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timezone import as_kyiv, now_kyiv
from app.models.db_types import StrEnum
import enum


class PlanTier(str, enum.Enum):
    free = "free"
    lite = "lite"
    standard = "standard"
    pro = "pro"


class Source(str, enum.Enum):
    auto_ria = "auto_ria"
    olx = "olx"
    telegram = "telegram"
    imperiya = "imperiya"
    udrive = "udrive"
    car_market = "car_market"
    reono = "reono"


class NotificationType(str, enum.Enum):
    listing_match = "listing_match"
    price_drop = "price_drop"
    vin_found = "vin_found"
    system = "system"


class ParseRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    partial = "partial"
    failed = "failed"


class SubscriptionStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    cancelled = "cancelled"
    failed = "failed"
    past_due = "past_due"


class SourceRequestStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    telegram_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_avatar_path: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plan: Mapped[PlanTier] = mapped_column(StrEnum(PlanTier), default=PlanTier.free)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String, default="USD")
    telegram_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    searches: Mapped[list["SearchQuery"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    billing_subscriptions: Mapped[list["BillingSubscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    source_requests: Mapped[list["MonitoringSourceRequest"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saved_comparisons: Mapped[list["SavedComparison"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def searches_limit(self) -> int:
        from app.services.billing.plans import effective_searches_limit
        return effective_searches_limit(self)

    @property
    def is_trial_active(self) -> bool:
        if self.trial_ends_at is None:
            return False
        return now_kyiv() < as_kyiv(self.trial_ends_at)

    @staticmethod
    def default_trial_end() -> datetime:
        from app.services.billing.plans import SIGNUP_TRIAL_DAYS

        return now_kyiv() + timedelta(days=SIGNUP_TRIAL_DAYS)


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    user: Mapped["User"] = relationship(back_populates="searches")
    search_listings: Mapped[list["SearchListing"]] = relationship(
        back_populates="search",
        cascade="all, delete-orphan",
    )


class SearchListing(Base):
    __tablename__ = "search_listings"
    __table_args__ = (UniqueConstraint("search_id", "listing_id", name="uq_search_listings_search_listing"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    search_id: Mapped[str] = mapped_column(String, ForeignKey("search_queries.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[str] = mapped_column(String, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    search: Mapped["SearchQuery"] = relationship(back_populates="search_listings")
    listing: Mapped["Listing"] = relationship(back_populates="search_listings")


class ParseRun(Base):
    __tablename__ = "parse_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    status: Mapped[ParseRunStatus] = mapped_column(StrEnum(ParseRunStatus), default=ParseRunStatus.running)
    triggered_by: Mapped[str] = mapped_column(String, default="scheduler")
    filter_groups: Mapped[int] = mapped_column(Integer, default=0)
    searches_processed: Mapped[int] = mapped_column(Integer, default=0)
    listings_found: Mapped[int] = mapped_column(Integer, default=0)
    listings_new: Mapped[int] = mapped_column(Integer, default=0)
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    log: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    external_id: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[Source] = mapped_column(StrEnum(Source))
    title: Mapped[str] = mapped_column(String)
    brand: Mapped[str] = mapped_column(String, index=True)
    model: Mapped[str] = mapped_column(String, index=True)
    year: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="UAH")
    mileage: Mapped[int] = mapped_column(Integer)
    fuel: Mapped[str] = mapped_column(String)
    transmission: Mapped[str] = mapped_column(String)
    region: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    images: Mapped[list] = mapped_column(JSON, default=list)
    url: Mapped[str] = mapped_column(String)
    seller_name: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_telegram: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_url: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_type: Mapped[str] = mapped_column(String, default="private")
    price_history: Mapped[list] = mapped_column(JSON, default=list)
    vin: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String, ForeignKey("listings.id"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    favorites: Mapped[list["Favorite"]] = relationship(back_populates="listing")
    search_listings: Mapped[list["SearchListing"]] = relationship(back_populates="listing")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    listing_id: Mapped[str] = mapped_column(String, ForeignKey("listings.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    user: Mapped["User"] = relationship(back_populates="favorites")
    listing: Mapped["Listing"] = relationship(back_populates="favorites")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(StrEnum(NotificationType))
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    listing_id: Mapped[str | None] = mapped_column(String, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    search_id: Mapped[str | None] = mapped_column(String, ForeignKey("search_queries.id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    user: Mapped["User"] = relationship(back_populates="notifications")


class TelegramChannel(Base):
    """Канали для парсингу Telethon — керуються з адмінки."""

    __tablename__ = "telegram_channels"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)


class MonitoringSourceRequest(Base):
    """Заявка користувача на додавання каналу / сайту для моніторингу."""

    __tablename__ = "monitoring_source_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[SourceRequestStatus] = mapped_column(
        StrEnum(SourceRequestStatus),
        default=SourceRequestStatus.pending,
        index=True,
    )
    admin_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kyiv,
        onupdate=now_kyiv,
    )

    user: Mapped["User"] = relationship(back_populates="source_requests")


class SavedComparison(Base):
    """Збережений список порівняння авто."""

    __tablename__ = "saved_comparisons"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    listing_ids: Mapped[list] = mapped_column(JSON, default=list)
    share_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kyiv,
        onupdate=now_kyiv,
    )

    user: Mapped["User"] = relationship(back_populates="saved_comparisons")


class BillingSubscription(Base):
    """Підписка LiqPay (джерело правди у нас; синхрон через callback)."""

    __tablename__ = "billing_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    order_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="UAH")
    periodicity: Mapped[str] = mapped_column(String, default="month")
    status: Mapped[SubscriptionStatus] = mapped_column(
        StrEnum(SubscriptionStatus),
        default=SubscriptionStatus.pending,
    )
    card_token: Mapped[str | None] = mapped_column(String, nullable=True)
    # Маска картки з LiqPay (напр. 424242******4242) — для кабінету.
    card_mask: Mapped[str | None] = mapped_column(String, nullable=True)
    liqpay_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String, nullable=True)
    # Поспільні невдалі рекурентні списання (скидається на success).
    failed_charges: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv, onupdate=now_kyiv)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="billing_subscriptions")
    payments: Mapped[list["BillingPayment"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class BillingPayment(Base):
    """Історія платежів / списань LiqPay (callback)."""

    __tablename__ = "billing_payments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subscription_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("billing_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id: Mapped[str] = mapped_column(String, index=True)
    plan: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="UAH")
    status: Mapped[str] = mapped_column(String)  # success | failure | ...
    liqpay_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    card_mask: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    subscription: Mapped["BillingSubscription | None"] = relationship(back_populates="payments")
