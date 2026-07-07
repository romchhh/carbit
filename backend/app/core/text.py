from __future__ import annotations


def norm_text(value: str | None) -> str:
    """Lowercase, collapse whitespace — для порівняння брендів, регіонів тощо."""
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())
