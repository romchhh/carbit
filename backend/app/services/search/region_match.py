"""Зіставлення регіону оголошення з фільтром (область → міста)."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.services.search.region_cities import REGION_CITIES, cities_for_region

# Невідома / загальноукраїнська локація — не відсікаємо за областю.
_GENERIC_LOCATIONS = frozenset(
    {
        "україна",
        "ukraine",
        "вся україна",
        "украина",
        "ua",
    }
)

# Короткі токени — лише з межами слова (щоб «бар» не ловив «барабан»).
_SHORT_KW_MAX = 3


def _keyword_in_blob(keyword: str, blob: str) -> bool:
    kw = (keyword or "").strip().lower()
    if not kw or not blob:
        return False
    if len(kw) <= _SHORT_KW_MAX:
        return bool(
            re.search(
                rf"(?<![a-zа-яёіїєґ0-9]){re.escape(kw)}(?![a-zа-яёіїєґ0-9])",
                blob,
                flags=re.IGNORECASE,
            )
        )
    return kw in blob


def listing_region_matches_filter(listing_region: str, filter_region: str) -> bool:
    """Чи підходить текст локації (або текст TG-поста) під обрану область/місто."""
    filter_key = norm_text(filter_region or "")
    if not filter_key or filter_key in ("вся україна", "ukraine"):
        return True

    blob = norm_text(listing_region or "")
    if not blob or blob in _GENERIC_LOCATIONS:
        # Немає точної локації — краще показати, ніж втратити (особливо Telegram).
        return True

    if filter_key == "м. київ":
        head = blob.split(",")[0].strip()
        if head in ("київ", "киев", "kyiv", "kiev") or head.startswith(
            ("київ ", "киев ", "kyiv ", "kiev ", "київ,", "киев,")
        ):
            return True
        # Авторинок: Бориспіль, Бровари тощо часто шукають разом із «м. Київ»
        metro = cities_for_region("м. київ")
        if metro and any(_keyword_in_blob(kw, blob) for kw in metro):
            return True
        return False

    # Повна назва області в тексті («Вінницька область», «Одеська обл.»)
    if filter_key in blob:
        return True
    # Скорочення «… обл.»
    oblast_short = filter_key.replace(" область", " обл")
    if oblast_short != filter_key and oblast_short in blob:
        return True

    keywords = cities_for_region(filter_key) or REGION_CITIES.get(filter_key, ())
    if keywords:
        return any(_keyword_in_blob(kw, blob) for kw in keywords)

    return filter_key in blob or blob in filter_key


# Зворотна сумісність для імпортів / тестів.
REGION_KEYWORDS = REGION_CITIES
