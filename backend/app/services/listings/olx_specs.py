"""Структуровані прапорці з OLX specs (ДТП, пригнано з США)."""

from __future__ import annotations

from app.core.text import norm_text

_USA_VALUE_TOKENS = ("сша", "usa", "america", "штати", "америк")


def olx_spec_condition_flags(specs: dict | None) -> dict[str, bool]:
    if not isinstance(specs, dict):
        return {}
    flags: dict[str, bool] = {}
    for key, raw in specs.items():
        if not isinstance(raw, str):
            continue
        key_n = norm_text(str(key))
        val_n = norm_text(raw)
        if "пригнано" in key_n or "car from" in key_n:
            if any(token in val_n for token in _USA_VALUE_TOKENS):
                flags["usa_import"] = True
        if "стан" in key_n or "condition" in key_n:
            if any(
                token in val_n
                for token in ("дтп", "accident", "після дтп", "бит", "after-an-accident")
            ):
                flags["had_accident"] = True
            if "не бит" in val_n or "not-bit" in val_n or "без дтп" in val_n:
                flags["not_damaged"] = True
    return flags
