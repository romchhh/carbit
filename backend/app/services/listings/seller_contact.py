"""Контакти продавця з джерел, де API/парсер їх реально надає."""

from __future__ import annotations

import re
from typing import Any

from app.schemas.schemas import ListingOut

# Продавці розділяють групи як завгодно, зокрема «0 97 555 44 33».
_PHONE_RE = re.compile(
    r"(?:\+?38)?[\s\-()]*0[\s\-()]*\d{2}[\s\-()]*\d{3}[\s\-()]*\d{2}[\s\-()]*\d{2}"
)
_USERNAME_RE = re.compile(r"(?:@|t\.me/)([A-Za-z0-9_]{3,32})", re.I)
_MASKED_PHONE_RE = re.compile(r"[xх*]{2,}|\.{3,}", re.I)
_DIGITS_RE = re.compile(r"\D+")


def is_usable_phone(value: str | None) -> bool:
    if not value or not str(value).strip():
        return False
    text = str(value).strip()
    if _MASKED_PHONE_RE.search(text):
        return False
    digits = _DIGITS_RE.sub("", text)
    return len(digits) >= 10


def normalize_phone(value: str) -> str:
    digits = _DIGITS_RE.sub("", value)
    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("80") and len(digits) == 11:
        return f"+3{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+38{digits}"
    if len(digits) == 9 and digits[0] in "3456789":
        return f"+380{digits}"
    return value.strip()


def normalize_telegram(value: str | None) -> str | None:
    if not value:
        return None
    username = str(value).strip().lstrip("@")
    if not username or not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username):
        return None
    return username


def extract_phone_from_text(text: str | None) -> str | None:
    if not text:
        return None
    match = _PHONE_RE.search(text)
    if not match:
        return None
    phone = normalize_phone(match.group(0))
    return phone if is_usable_phone(phone) else None


def extract_telegram_from_text(text: str | None) -> str | None:
    if not text:
        return None
    match = _USERNAME_RE.search(text)
    if not match:
        return None
    return normalize_telegram(match.group(1))


def seller_contact_from_auto_ria(info: dict[str, Any]) -> dict[str, str | None]:
    """AUTO.RIA не повертає реальний телефон у /auto/info — лише маскований."""
    dealer = info.get("dealer") if isinstance(info.get("dealer"), dict) else {}
    name = str(dealer.get("name") or "").strip() or None
    link = str(dealer.get("link") or "").strip() or None
    if link and not link.startswith("http"):
        from app.services.auto_ria.constants import AUTO_RIA_SITE_URL

        link = f"{AUTO_RIA_SITE_URL}{link}"
    return {
        "seller_name": name,
        "seller_phone": None,
        "seller_telegram": None,
        "seller_url": link,
    }


def seller_contact_from_auto_ria_salon(salon: dict[str, Any]) -> dict[str, str | None]:
    name = str(salon.get("name") or salon.get("title") or "").strip() or None
    link = str(salon.get("link") or salon.get("url") or "").strip() or None
    if link and not link.startswith("http"):
        from app.services.auto_ria.constants import AUTO_RIA_SITE_URL

        link = f"{AUTO_RIA_SITE_URL}{link}"
    return {
        "seller_name": name,
        "seller_phone": None,
        "seller_telegram": None,
        "seller_url": link,
    }


def seller_contact_from_imperiya(ad: dict[str, Any]) -> dict[str, str | None]:
    dealer = ad.get("dealer") if isinstance(ad.get("dealer"), dict) else {}
    contact = ad.get("contact") if isinstance(ad.get("contact"), dict) else {}

    name = str(dealer.get("name") or contact.get("name") or "").strip() or None
    slug = str(dealer.get("slug") or "").strip()
    seller_url = f"https://imperiya-auto.com.ua/dealer/{slug}" if slug else None

    return {
        "seller_name": name,
        "seller_phone": None,
        "seller_telegram": None,
        "seller_url": seller_url,
    }


def seller_contact_from_telegram(
    *,
    phone: str | None = None,
    contact_username: str | None = None,
    description: str | None = None,
) -> dict[str, str | None]:
    resolved_phone = None
    if phone and is_usable_phone(phone):
        resolved_phone = normalize_phone(phone)
    elif phone:
        resolved_phone = extract_phone_from_text(phone)
    if not resolved_phone:
        resolved_phone = extract_phone_from_text(description)

    resolved_tg = normalize_telegram(contact_username) or extract_telegram_from_text(description)

    return {
        "seller_name": None,
        "seller_phone": resolved_phone,
        "seller_telegram": resolved_tg,
        "seller_url": None,
    }


def seller_contact_from_source_data(source: str, source_data: dict[str, Any] | None) -> dict[str, str | None]:
    if not source_data:
        return {
            "seller_name": None,
            "seller_phone": None,
            "seller_telegram": None,
            "seller_url": None,
        }

    if source == "telegram":
        return seller_contact_from_telegram(
            phone=source_data.get("phone") if isinstance(source_data.get("phone"), str) else None,
            contact_username=(
                source_data.get("contact_username")
                if isinstance(source_data.get("contact_username"), str)
                else None
            ),
        )

    if source == "imperiya":
        imperiya = source_data.get("imperiya")
        if isinstance(imperiya, dict):
            return seller_contact_from_imperiya(imperiya)
        return seller_contact_from_imperiya(source_data)

    return {
        "seller_name": None,
        "seller_phone": None,
        "seller_telegram": None,
        "seller_url": None,
    }


def merge_seller_contact(base: dict[str, str | None], extra: dict[str, str | None]) -> dict[str, str | None]:
    merged = dict(base)
    for key, value in extra.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged


def apply_seller_contact_fields(listing: ListingOut, contact: dict[str, str | None]) -> ListingOut:
    updates = {key: value for key, value in contact.items() if value}
    if not updates:
        return listing
    return listing.model_copy(update=updates)


def enrich_listing_seller_contact(listing: ListingOut) -> ListingOut:
    """Доповнює контакт з source_data / опису, якщо поля ще порожні."""
    current = {
        "seller_name": listing.seller_name,
        "seller_phone": listing.seller_phone,
        "seller_telegram": listing.seller_telegram,
        "seller_url": listing.seller_url,
    }
    if all(current.values()):
        return listing

    from_source = seller_contact_from_source_data(listing.source, listing.source_data)
    merged = merge_seller_contact(current, from_source)

    if listing.source == "telegram" and (not merged["seller_phone"] or not merged["seller_telegram"]):
        from_text = seller_contact_from_telegram(description=listing.description)
        merged = merge_seller_contact(merged, from_text)

    updates = {key: value for key, value in merged.items() if value and not getattr(listing, key, None)}
    if not updates:
        return listing
    return listing.model_copy(update=updates)


def listing_has_seller_contact(listing: ListingOut) -> bool:
    return bool(listing.seller_name or listing.seller_phone or listing.seller_telegram or listing.seller_url)
