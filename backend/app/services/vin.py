"""Витяг VIN з довільного тексту оголошення (OLX / Telegram / опис)."""

from __future__ import annotations

import re

# 17 символів без I/O/Q (стандарт ISO 3779).
_VIN_CANDIDATE_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
_VIN_LABELED_RE = re.compile(
    r"(?:vin|він|вин(?:[\s\-]*код)?)\s*[:\-–—]?\s*([A-HJ-NPR-Z0-9]{17})",
    re.IGNORECASE,
)
_VIN_HASHTAG_RE = re.compile(r"#([A-HJ-NPR-Z0-9]{17})\b", re.IGNORECASE)
# VIN з пробілами/дефісами між групами — НЕ суцільний склеєний текст оголошення.
_SPACED_VIN_RE = re.compile(
    r"(?<![A-HJ-NPR-Z0-9])"
    r"(?:[A-HJ-NPR-Z0-9]{2,8}[\s\-]+){1,6}[A-HJ-NPR-Z0-9]{2,8}"
    r"(?![A-HJ-NPR-Z0-9])",
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
    Порядок: хештег → «VIN: …» → суцільний 17-символьний → spaced групами.
    Compact по всьому тексту не робимо — дає хибні VIN з «Facelift Zeekr 001…».
    """
    chunks = [str(part) for part in parts if part]
    if not chunks:
        return None

    blob = "\n".join(chunks)
    upper = blob.upper()

    for match in _VIN_HASHTAG_RE.finditer(blob):
        candidate = match.group(1).upper()
        if is_valid_vin(candidate):
            return candidate

    labeled = _VIN_LABELED_RE.search(blob)
    if labeled:
        candidate = labeled.group(1).upper()
        if is_valid_vin(candidate):
            return candidate

    for match in _VIN_CANDIDATE_RE.finditer(upper):
        candidate = match.group(0)
        if is_valid_vin(candidate):
            return candidate

    for match in _SPACED_VIN_RE.finditer(upper):
        candidate = re.sub(r"[^A-HJ-NPR-Z0-9]", "", match.group(0))
        if is_valid_vin(candidate):
            return candidate

    return None
