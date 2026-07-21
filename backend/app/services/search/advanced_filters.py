"""Розширені фільтри (як AUTO.RIA advanced): місця, потужність, привід тощо."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.olx.constants import COLOR_NAME_TO_TOKEN, DRIVETRAIN_NAME_TO_TOKEN

_SEATS_NUMBER = re.compile(
    r"(?:seats?|місць|міс\.?|мест)\s*[:\-]?\s*(\d{1,2})",
    re.IGNORECASE,
)


def advanced_filters_active(filters: SearchFilters) -> bool:
    return any(
        [
            filters.seats_from is not None,
            filters.seats_to is not None,
            filters.engine_volume_from is not None,
            filters.engine_volume_to is not None,
            filters.power_from is not None,
            filters.power_to is not None,
            filters.fuel_consumption_from is not None,
            filters.fuel_consumption_to is not None,
            filters.ev_range_from is not None,
            filters.ev_range_to is not None,
            filters.battery_capacity_from is not None,
            filters.battery_capacity_to is not None,
            bool(filters.drivetrain),
            bool(filters.colors),
        ]
    )


def extract_listing_seats(item: ListingOut) -> int | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    for key in ("seats", "seat", "seatsInt", "seatInt"):
        raw = auto.get(key) if auto else sd.get(key)
        if raw is not None:
            digits = re.sub(r"[^\d]", "", str(raw))
            if digits:
                value = int(digits)
                if 1 <= value <= 20:
                    return value

    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}
    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        key = str(spec_key).lower()
        if "міс" in key or "seat" in key or "сидяч" in key:
            digits = re.sub(r"[^\d]", "", spec_value)
            if digits:
                value = int(digits)
                if 1 <= value <= 20:
                    return value

    blob = f"{item.title} {item.description or ''}"
    for pattern in (_SEATS_NUMBER, re.compile(r"(\d)\s*[x×]\s*(\d)\s*(?:міс|мест)", re.I)):
        m = pattern.search(blob)
        if m:
            if m.lastindex and m.lastindex >= 2:
                a, b = int(m.group(1)), int(m.group(2))
                total = a * b if a <= 3 and b <= 4 else max(a, b)
            else:
                total = int(m.group(1))
            if 1 <= total <= 20:
                return total

    m = re.search(r"(\d{1,2})\s*(?:місць|міс\.?|мест)\b", blob, re.I)
    if m:
        value = int(m.group(1))
        if 1 <= value <= 20:
            return value
    return None


def _seats_in_range(seats: int, filters: SearchFilters) -> bool:
    if filters.seats_from is not None and seats < filters.seats_from:
        return False
    if filters.seats_to is not None and seats > filters.seats_to:
        return False
    return True


def listing_matches_seats_filter(item: ListingOut, filters: SearchFilters) -> bool:
    if filters.seats_from is None and filters.seats_to is None:
        return True
    seats = extract_listing_seats(item)
    if seats is None:
        return False
    return _seats_in_range(seats, filters)


def _spec_number_from_listing(item: ListingOut, *keys: str) -> float | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}

    for source in (auto, specs):
        for spec_key, spec_value in source.items():
            if not isinstance(spec_value, (str, int, float)):
                continue
            if any(k.lower() in str(spec_key).lower() for k in keys):
                if isinstance(spec_value, (int, float)):
                    return float(spec_value)
                match = re.search(r"[\d]+[.,]?\d*", str(spec_value).replace(" ", ""))
                if match:
                    return float(match.group(0).replace(",", "."))

    blob = norm_text(f"{item.title} {item.description or ''} {item.fuel} {item.transmission}")
    for key in keys:
        match = re.search(rf"{re.escape(key.lower())}[^\d]{{0,12}}([\d]+[.,]?\d*)", blob)
        if match:
            try:
                return float(match.group(1).replace(",", "."))
            except ValueError:
                continue
    return None


def listing_matches_advanced_filters(item: ListingOut, filters: SearchFilters) -> bool:
    if not advanced_filters_active(filters):
        return True

    if not listing_matches_seats_filter(item, filters):
        return False

    if filters.engine_volume_from is not None or filters.engine_volume_to is not None:
        engine = _spec_number_from_listing(item, "об'єм", "объем", "engine", "двигун")
        if engine is not None:
            if filters.engine_volume_from is not None and engine < filters.engine_volume_from:
                return False
            if filters.engine_volume_to is not None and engine > filters.engine_volume_to:
                return False

    if filters.power_from is not None or filters.power_to is not None:
        power = _spec_number_from_listing(item, "потужність", "power", "к.с", "л.с")
        if power is not None:
            if filters.power_from is not None and power < filters.power_from:
                return False
            if filters.power_to is not None and power > filters.power_to:
                return False

    if filters.fuel_consumption_from is not None or filters.fuel_consumption_to is not None:
        consumption = _spec_number_from_listing(item, "витрат", "consumption")
        if consumption is not None:
            if filters.fuel_consumption_from is not None and consumption < filters.fuel_consumption_from:
                return False
            if filters.fuel_consumption_to is not None and consumption > filters.fuel_consumption_to:
                return False

    if filters.ev_range_from is not None or filters.ev_range_to is not None:
        ev_range = _spec_number_from_listing(item, "запас ходу", "range")
        if ev_range is not None:
            if filters.ev_range_from is not None and ev_range < filters.ev_range_from:
                return False
            if filters.ev_range_to is not None and ev_range > filters.ev_range_to:
                return False

    if filters.battery_capacity_from is not None or filters.battery_capacity_to is not None:
        battery = _spec_number_from_listing(item, "акумулятор", "battery", "кВт")
        if battery is not None:
            if filters.battery_capacity_from is not None and battery < filters.battery_capacity_from:
                return False
            if filters.battery_capacity_to is not None and battery > filters.battery_capacity_to:
                return False

    blob = norm_text(f"{item.title} {item.description or ''} {item.fuel} {item.transmission}")
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}
    specs_blob = norm_text(" ".join(str(v) for v in specs.values() if isinstance(v, str)))
    haystack = f"{blob} {specs_blob}"

    if filters.drivetrain:
        if specs_blob:
            matched = any(
                DRIVETRAIN_NAME_TO_TOKEN.get(norm_text(d), norm_text(d)) in specs_blob
                or norm_text(d) in specs_blob
                for d in filters.drivetrain
            )
            if not matched:
                return False

    if filters.colors:
        if specs_blob:
            matched = any(
                COLOR_NAME_TO_TOKEN.get(norm_text(c), norm_text(c)) in specs_blob
                for c in filters.colors
            )
            if not matched:
                return False

    return True
