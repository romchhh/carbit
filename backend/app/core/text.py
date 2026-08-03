from __future__ import annotations


def norm_text(value: str | None) -> str:
    """Lowercase, collapse whitespace — для порівняння брендів, регіонів тощо."""
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def bounded_substring(hay: str, needle: str) -> bool:
    """Чи є needle у hay на межі токена («c-class» ≠ всередині «glc-class»)."""
    if not hay or not needle:
        return False
    if hay == needle:
        return True
    idx = hay.find(needle)
    while idx != -1:
        before_ok = idx == 0 or not hay[idx - 1].isalnum()
        end = idx + len(needle)
        after_ok = end == len(hay) or not hay[end].isalnum()
        if before_ok and after_ok:
            return True
        idx = hay.find(needle, idx + 1)
    return False
