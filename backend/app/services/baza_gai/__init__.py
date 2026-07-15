"""Клієнт API Бази ДАІ (baza-gai.com.ua) — перевірка VIN / номерів."""

from app.services.baza_gai.service import lookup_vin

__all__ = ["lookup_vin"]
