from datetime import datetime
from typing import Optional
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


class TelegramLoginRequest(BaseModel):
    token: str = Field(min_length=10)


class TelegramLoginUrlOut(BaseModel):
    bot_url: str
    bot_username: str


class GoogleAuthUrlOut(BaseModel):
    url: str


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


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
    mileage_from: Optional[int] = None
    mileage_to: Optional[int] = None
    fuel: Optional[list[str]] = None
    transmission: Optional[list[str]] = None
    region: Optional[str] = None
    sources: Optional[list[str]] = None


class SearchQueryCreate(BaseModel):
    name: str
    filters: SearchFilters


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

    model_config = {"from_attributes": True}


# Listing
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
    price_history: list[dict]
    is_duplicate: bool
    published_at: datetime
    found_at: datetime

    model_config = {"from_attributes": True}


class PaginatedListings(BaseModel):
    items: list[ListingOut]
    total: int
    page: int
    per_page: int
    pages: int


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

    model_config = {"from_attributes": True}


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


class SubscriptionOut(BaseModel):
    plan: str
    plan_name: str
    searches_limit: int
    plan_expires_at: datetime | None
    trial_ends_at: datetime | None
    is_trial_active: bool


class SubscribeRequest(BaseModel):
    plan: str = Field(pattern=r"^(free|lite|standard|pro)$")


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
