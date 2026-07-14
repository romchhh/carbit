from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendCodeRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
    expires_in: int | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = True


class TelegramLoginRequest(BaseModel):
    token: str = Field(min_length=10)


class TelegramLoginUrlOut(BaseModel):
    bot_url: str
    bot_username: str


class GoogleAuthUrlOut(BaseModel):
    url: str


class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    preferred_currency: Optional[str] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Введіть ім'я")
        return stripped

    @field_validator("preferred_currency", mode="before")
    @classmethod
    def normalize_preferred_currency(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        from app.services.currency import resolve_display_currency

        return resolve_display_currency(str(value))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# User
class UserOut(BaseModel):
    id: str
    email: str
    name: str
    plan: str
    searches_limit: int
    telegram_connected: bool
    telegram_username: str | None = None
    avatar_url: str | None = None
    email_verified: bool = False
    trial_ends_at: datetime | None = None
    is_trial_active: bool = False
    onboarding_completed: bool = False
    plan_expires_at: datetime | None = None
    preferred_currency: str = "USD"
    created_at: datetime

    model_config = {"from_attributes": True}


class OnboardingCompleteRequest(BaseModel):
    completed: bool = True


class EmailBindSendRequest(BaseModel):
    email: EmailStr


class EmailBindVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


# Search filters
class SearchFilters(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    price_from: Optional[int] = None
    price_to: Optional[int] = None
    # Валюта діапазону ціни: USD (AUTO.RIA currency=1) або UAH (currency=3).
    # None = UAH (зворотна сумісність зі збереженими пошуками).
    currency: Optional[str] = None
    mileage_from: Optional[int] = None
    mileage_to: Optional[int] = None
    fuel: Optional[list[str]] = None
    transmission: Optional[list[str]] = None
    region: Optional[str] = None
    sources: Optional[list[str]] = None
    category: Optional[str] = None
    engine_volume_from: Optional[float] = None
    engine_volume_to: Optional[float] = None
    drivetrain: Optional[list[str]] = None
    colors: Optional[list[str]] = None
    fuel_consumption_from: Optional[float] = None
    fuel_consumption_to: Optional[float] = None
    ev_range_from: Optional[int] = None
    ev_range_to: Optional[int] = None
    battery_capacity_from: Optional[float] = None
    battery_capacity_to: Optional[float] = None
    power_from: Optional[int] = None
    power_to: Optional[int] = None
    # Тільки оголошення, опубліковані за останні N днів (напр. 7 = «тільки нові»)
    published_within_days: Optional[int] = Field(default=None, ge=1, le=90)
    # Для моніторингу / Telegram: лише оголошення за останні N годин
    published_within_hours: Optional[int] = Field(default=None, ge=1, le=168)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        cur = str(value).strip().upper()
        if cur in {"USD", "UAH", "EUR"}:
            return cur
        if cur in {"$", "US"}:
            return "USD"
        if cur in {"ГРН", "UA"}:
            return "UAH"
        if cur in {"€", "EU", "EURO"}:
            return "EUR"
        return None


class SearchQueryCreate(BaseModel):
    name: str
    filters: SearchFilters
    # Авто з першого live-пошуку — базовий знімок (не як «нові»).
    seed_listings: list[Any] = Field(default_factory=list)

class SearchQueryUpdate(BaseModel):
    name: Optional[str] = None
    filters: Optional[SearchFilters] = None
    is_active: Optional[bool] = None


class SearchQueryOut(BaseModel):
    id: str
    name: str
    filters: dict
    is_active: bool
    new_count: int
    total_count: int
    last_checked_at: Optional[datetime]
    created_at: datetime
    # Перше фото найновішого авто в моніторингу (для прев’ю в списку).
    preview_image: Optional[str] = None

    model_config = {"from_attributes": True}


# Listing
class ListingSourceLink(BaseModel):
    """Посилання на те саме авто в іншому джерелі (для UI іконок)."""

    source: str
    url: str
    id: Optional[str] = None


class ListingOut(BaseModel):
    id: str
    source: str
    title: str
    brand: str
    model: str
    year: int
    price: int
    currency: str
    mileage: int
    fuel: str
    transmission: str
    region: str
    description: Optional[str]
    images: list[str]
    url: str
    seller_type: str
    vin: Optional[str] = None
    vin_checked: Optional[bool] = None
    vin_check_url: Optional[str] = None
    source_data: Optional[dict[str, Any]] = None
    price_history: list[dict]
    is_duplicate: bool
    duplicate_of: Optional[str] = None
    alternate_sources: list[ListingSourceLink] = Field(default_factory=list)
    # Для результатів моніторингу: чи авто ще не переглянуте як «нове».
    is_new: Optional[bool] = None
    published_at: datetime
    refreshed_at: Optional[datetime] = None
    found_at: datetime

    model_config = {"from_attributes": True}


class SourceStatusOut(BaseModel):
    source: str
    item_count: int = 0
    error: Optional[str] = None
    pending: bool = False


class PaginatedListings(BaseModel):
    items: list[ListingOut]
    total: int
    page: int
    per_page: int
    pages: int
    sources: list[SourceStatusOut] = Field(default_factory=list)
    partial: bool = False
    from_cache: bool = False


class SearchLiveResultsOut(BaseModel):
    search: SearchQueryOut
    results: PaginatedListings


# Dashboard
class DashboardStats(BaseModel):
    active_searches: int
    searches_limit: int
    new_listings_today: int
    new_listings_yesterday: int
    favorites_count: int
    unread_notifications: int
    sources_count: int = 3
    plan: str
    is_trial_active: bool


# Favorites
class FavoriteOut(BaseModel):
    id: str
    listing_id: str
    listing: ListingOut
    created_at: datetime

    model_config = {"from_attributes": True}


class FavoriteCreate(BaseModel):
    listing_id: str
    listing: Optional[ListingOut] = None


class FavoriteCheckBatch(BaseModel):
    listing_ids: list[str] = Field(default_factory=list)


# Notifications
class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    listing_id: str | None
    search_id: str | None
    payload: dict
    is_read: bool
    sent_telegram: bool
    created_at: datetime
    listing: ListingOut | None = None


class PaginatedNotifications(BaseModel):
    items: list[NotificationOut]
    total: int
    unread: int
    page: int
    per_page: int


class NotificationStats(BaseModel):
    unread: int
    total: int


# Billing
class PlanOut(BaseModel):
    id: str
    name: str
    description: str
    searches_limit: int
    requests_month: int
    requests_hour: int
    price_uah: int
    features: list[str]


class BillingPaymentOut(BaseModel):
    id: str
    order_id: str
    plan: str
    plan_name: str
    amount: int
    currency: str
    status: str
    card_mask: str | None = None
    description: str | None = None
    paid_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    plan: str
    plan_name: str
    searches_limit: int
    plan_expires_at: datetime | None
    trial_ends_at: datetime | None
    is_trial_active: bool
    liqpay_enabled: bool = False
    # Наступне списання / кінець оплаченого періоду.
    next_payment_at: datetime | None = None
    # Маска картки LiqPay (•••• 4242).
    card_mask: str | None = None
    recurring_active: bool = False
    payments: list[BillingPaymentOut] = Field(default_factory=list)


class SubscribeRequest(BaseModel):
    plan: str = Field(pattern=r"^(free|lite|standard|pro)$")
    apply_credit: bool = True


class UpgradeQuoteOut(BaseModel):
    current_plan: str
    current_plan_name: str
    current_price_uah: int
    target_plan: str
    target_plan_name: str
    target_price_uah: int
    target_searches_limit: int
    days_remaining: int
    period_days: int
    target_period_days: int
    credit_uah: int
    amount_due_uah: int
    enable_subscribe: bool
    is_upgrade: bool
    is_free_upgrade: bool
    recommended: bool = False


class CheckoutOut(BaseModel):
    order_id: str
    checkout_url: str
    data: str
    signature: str
    amount: int
    currency: str
    plan: str
    plan_name: str
    credit_uah: int = 0
    list_price_uah: int | None = None
    enable_subscribe: bool = True
    free_upgrade: bool = False


# Telegram
class TelegramConnectLinkOut(BaseModel):
    bot_url: str
    bot_username: str
    expires_in: int


class TelegramStatusOut(BaseModel):
    connected: bool
    telegram_username: str | None = None
    telegram_id: str | None = None


class TelegramRegisterInfoOut(BaseModel):
    name: str
    email: str
    valid: bool
    telegram_only: bool = False


class TelegramRegisterCompleteRequest(BaseModel):
    token: str = Field(min_length=10)


class TelegramRegisterCompleteOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
