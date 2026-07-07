import uuid
from datetime import datetime, timedelta

from sqlalchemy import String, Boolean, DateTime, Integer, JSON, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timezone import as_kyiv, now_kyiv
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


class NotificationType(str, enum.Enum):
    listing_match = "listing_match"
    price_drop = "price_drop"
    system = "system"


class ParseRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    partial = "partial"
    failed = "failed"


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
    plan: Mapped[PlanTier] = mapped_column(SAEnum(PlanTier), default=PlanTier.free)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    searches: Mapped[list["SearchQuery"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def searches_limit(self) -> int:
        from app.services.billing.plans import get_plan
        return get_plan(self.plan.value)["searches_limit"]

    @property
    def is_trial_active(self) -> bool:
        if self.trial_ends_at is None:
            return False
        return now_kyiv() < as_kyiv(self.trial_ends_at)

    @staticmethod
    def default_trial_end() -> datetime:
        return now_kyiv() + timedelta(days=3)


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
    status: Mapped[ParseRunStatus] = mapped_column(SAEnum(ParseRunStatus), default=ParseRunStatus.running)
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
    source: Mapped[Source] = mapped_column(SAEnum(Source))
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
    seller_type: Mapped[str] = mapped_column(String, default="private")
    price_history: Mapped[list] = mapped_column(JSON, default=list)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String, ForeignKey("listings.id"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
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
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    listing_id: Mapped[str | None] = mapped_column(String, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    search_id: Mapped[str | None] = mapped_column(String, ForeignKey("search_queries.id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kyiv)

    user: Mapped["User"] = relationship(back_populates="notifications")
