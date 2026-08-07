"""Нормалізація українських номерів телефону."""

from __future__ import annotations

import re

PHONE_PLACEHOLDER_EMAIL_SUFFIX = "@phone.carbit.local"


class PhoneValidationError(ValueError):
    pass


def normalize_ua_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("380"):
        normalized = digits
    elif digits.startswith("80") and len(digits) == 11:
        normalized = f"3{digits}"
    elif digits.startswith("0") and len(digits) == 10:
        normalized = f"38{digits}"
    elif len(digits) == 9:
        normalized = f"380{digits}"
    else:
        normalized = digits

    if not re.fullmatch(r"380\d{9}", normalized):
        raise PhoneValidationError("Невірний формат номера. Вкажіть український номер, наприклад +380 67 123 45 67")

    return normalized


def phone_placeholder_email(phone: str) -> str:
    return f"{normalize_ua_phone(phone)}{PHONE_PLACEHOLDER_EMAIL_SUFFIX}"


def is_phone_placeholder_email(email: str) -> bool:
    return str(email or "").endswith(PHONE_PLACEHOLDER_EMAIL_SUFFIX)


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) != 12 or not digits.startswith("380"):
        return phone
    return f"+380 {digits[3:5]} *** {digits[7:9]} {digits[9:12]}"


def format_phone_display(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) != 12 or not digits.startswith("380"):
        return phone
    return f"+380 {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"
