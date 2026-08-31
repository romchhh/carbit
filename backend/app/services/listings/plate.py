"""Держномер авто: AUTO.RIA, текст оголошення, інші джерела."""

from __future__ import annotations

import re

from app.schemas.schemas import ListingOut

# Стандарт UA: AA1234BB / AA 1234 BB (латиниця або кирилиця схожих літер).
_PLATE_BODY_RE = re.compile(
    r"(?<![A-ZА-ЯІЇЄҐ0-9])"
    r"([A-ZА-ЯІЇЄҐ]{2}\s?\d{4}\s?[A-ZА-ЯІЇЄҐ]{2})"
    r"(?![A-ZА-ЯІЇЄҐ0-9])",
    re.IGNORECASE,
)

_CYR_TO_LAT = str.maketrans(
    {
        # Кирилиця, яку продавці інколи вводять замість латиниці в номері.
        "А": "A",
        "В": "B",
        "Е": "E",
        "І": "I",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Т": "T",
        "У": "Y",
        "Х": "X",
        "а": "A",
        "в": "B",
        "е": "E",
        "і": "I",
        "к": "K",
        "м": "M",
        "н": "H",
        "о": "O",
        "р": "P",
        "с": "C",
        "т": "T",
        "у": "Y",
        "х": "X",
    }
)


def normalize_ua_plate(raw: str | None) -> str | None:
    """«BX5318YA» / «BX 5318 YA» → «BX 5318 YA»."""
    text = (raw or "").strip()
    if not text:
        return None
    compact = re.sub(r"[^A-Za-zА-Яа-яІіЇїЄєҐґ0-9]", "", text).translate(_CYR_TO_LAT).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{4}[A-Z]{2}", compact):
        return None
    return f"{compact[:2]} {compact[2:6]} {compact[6:]}"


def extract_plate_from_text(*chunks: str | None) -> str | None:
    """Шукає держномер у заголовку / описі (Telegram, OLX, тощо)."""
    blob = "\n".join(part for part in chunks if part and str(part).strip())
    if not blob:
        return None
    for match in _PLATE_BODY_RE.finditer(blob):
        plate = normalize_ua_plate(match.group(1))
        if plate:
            return plate
    return None


def _olx_param_plate_text(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("key") or value.get("label") or "").strip()
    if value is None:
        return ""
    return str(value).strip()


def plate_from_olx_params(params: object) -> str | None:
    """OLX offers API / __PRERENDERED_STATE__: params[].license_plate."""
    if not isinstance(params, list):
        return None
    for item in params:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").lower()
        name = str(item.get("name") or "").lower()
        if key != "license_plate" and "license" not in key and "держ" not in name:
            continue
        plate = normalize_ua_plate(_olx_param_plate_text(item.get("value")))
        if plate:
            return plate
    return None


def _plate_from_olx_source_data(source_data: dict) -> str | None:
    raw_params = source_data.get("raw_params")
    if isinstance(raw_params, dict):
        plate = plate_from_olx_params(raw_params.get("params"))
        if plate:
            return plate

    specs = source_data.get("specs")
    if isinstance(specs, dict):
        for spec_key, spec_value in specs.items():
            key_low = str(spec_key).lower()
            if "держ" not in key_low and "license" not in key_low and "номер реєстр" not in key_low:
                continue
            plate = normalize_ua_plate(str(spec_value) if spec_value is not None else None)
            if plate:
                return plate
    return None


def _plate_from_source_data(source_data: dict | None) -> str | None:
    if not isinstance(source_data, dict):
        return None
    raw = source_data.get("plateNumber")
    if isinstance(raw, str):
        plate = normalize_ua_plate(raw)
        if plate:
            return plate
    block = source_data.get("plateNumberData")
    if isinstance(block, dict):
        text = block.get("text")
        if isinstance(text, str):
            plate = normalize_ua_plate(text)
            if plate:
                return plate

    imperiya = source_data.get("imperiya")
    if isinstance(imperiya, dict):
        plate = normalize_ua_plate(imperiya.get("plateNumber") if isinstance(imperiya.get("plateNumber"), str) else None)
        if plate:
            return plate

    reono = source_data.get("reono")
    if isinstance(reono, dict):
        for field in ("plateNumber", "plate"):
            raw_reono = reono.get(field)
            if isinstance(raw_reono, str):
                plate = normalize_ua_plate(raw_reono)
                if plate:
                    return plate

    return _plate_from_olx_source_data(source_data)


def resolve_listing_plate(listing: ListingOut) -> str | None:
    if listing.plate:
        plate = normalize_ua_plate(listing.plate)
        if plate:
            return plate
    plate = _plate_from_source_data(listing.source_data)
    if plate:
        return plate
    return extract_plate_from_text(listing.title, listing.description)


def enrich_listing_plate(listing: ListingOut) -> ListingOut:
    plate = resolve_listing_plate(listing)
    if not plate:
        return listing
    if listing.plate == plate:
        return listing
    return listing.model_copy(update={"plate": plate})
