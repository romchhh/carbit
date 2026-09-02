"""Текстовий haystack оголошення для фільтрів і прапорців."""

from __future__ import annotations

from app.core.text import norm_text
from app.schemas.schemas import ListingOut


def listing_search_haystack(item: ListingOut) -> str:
    """Те саме, що advanced_filters: title + specs + autoData."""
    blob = norm_text(f"{item.title} {item.description or ''} {item.fuel} {item.transmission}")
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}
    specs_blob = norm_text(" ".join(str(v) for v in specs.values() if isinstance(v, str)))
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    auto_blob = norm_text(
        " ".join(str(v) for v in auto.values() if isinstance(v, (str, int, float)))
    )
    return f"{blob} {specs_blob} {auto_blob}"
