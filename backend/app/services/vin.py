"""Витяг VIN з довільного тексту оголошення (OLX / Telegram / опис)."""

from __future__ import annotations

import re

# 17 символів без I/O/Q (стандарт ISO 3779).
_VIN_CANDIDATE_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
_VIN_LABELED_RE = re.compile(
    r"(?:vin|він|вин(?:[\s\-]*код)?)\s*[:\-–—]?\s*([A-HJ-NPR-Z0-9]{17})",
    re.IGNORECASE,
)


def is_valid_vin(value: str | None) -> bool:
    if not value:
        return False
    vin = value.strip().upper()
    if len(vin) != 17:
        return False
    if any(ch in vin for ch in "IOQ"):
        return False
    return bool(re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin))


def extract_vin(*parts: str | None) -> str | None:
    """
    Шукає VIN у переданих фрагментах тексту.
    Спочатку «VIN: XXX…», потім будь-який валідний 17-символьний код.
    """
    chunks = [str(part) for part in parts if part]
    if not chunks:
        return None

    blob = "\n".join(chunks)
    upper = blob.upper()

    labeled = _VIN_LABELED_RE.search(blob)
    if labeled:
        candidate = labeled.group(1).upper()
        if is_valid_vin(candidate):
            return candidate

    for match in _VIN_CANDIDATE_RE.finditer(upper):
        candidate = match.group(0)
        if is_valid_vin(candidate):
            return candidate

    # Іноді VIN пишуть з пробілами/дефісами: W1N WH5AB1 SX014976
    compact = re.sub(r"[^A-HJ-NPR-Z0-9]", "", upper)
    for i in range(0, max(len(compact) - 16, 0)):
        candidate = compact[i : i + 17]
        if is_valid_vin(candidate):
            return candidate

    return None
