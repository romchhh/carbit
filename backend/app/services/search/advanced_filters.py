"""Розширені фільтри (як AUTO.RIA advanced): місця, потужність, привід тощо."""

from __future__ import annotations

import re

from app.core.text import norm_text
from app.schemas.schemas import ListingOut, SearchFilters
from app.services.auto_ria.filter_maps import BODY_TYPE_TO_ID
from app.services.olx.constants import COLOR_NAME_TO_TOKEN, DRIVETRAIN_NAME_TO_TOKEN

_SEATS_NUMBER = re.compile(
    r"(?:seats?|місць|міс\.?|мест)\s*[:\-]?\s*(\d{1,2})",
    re.IGNORECASE,
)

_BODY_ALIASES: dict[str, tuple[str, ...]] = {
    "седан": ("sedan", "седан"),
    "універсал": ("універсал", "universal", "wagon"),
    "хетчбек": ("хетчбек", "hatchback"),
    "купе": ("купе", "coupe"),
    "мінівен": ("мінівен", "minivan"),
    "позашляховик": ("позашляховик", "suv", "внедорожник"),
    "кросовер": ("кросовер", "crossover"),
    "пікап": ("пікап", "pickup"),
    "ліфтбек": ("ліфтбек", "liftback"),
}


def advanced_filters_active(filters: SearchFilters) -> bool:
    return any(
        [
            filters.seats_from is not None,
            filters.seats_to is not None,
            filters.doors_from is not None,
            filters.doors_to is not None,
            bool(filters.body_types),
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
            filters.seller_filter,
            filters.accident,
            filters.zero_mileage,
            filters.bargain,
            filters.vin_verified,
            filters.owners_max is not None,
            filters.in_credit,
            filters.usa_import,
            filters.not_customs,
            filters.metallic,
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


def extract_listing_doors(item: ListingOut) -> int | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    for key in ("door", "doors", "doorCount", "doorInt"):
        raw = auto.get(key)
        if raw is not None:
            digits = re.sub(r"[^\d]", "", str(raw))
            if digits:
                value = int(digits)
                if 2 <= value <= 7:
                    return value
    m = re.search(r"(\d)\s*(?:двер|door)", f"{item.title} {item.description or ''}", re.I)
    if m:
        value = int(m.group(1))
        if 2 <= value <= 7:
            return value
    return None


def extract_listing_owners(item: ListingOut) -> int | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    for key in ("ownerCount", "owners", "owner"):
        raw = auto.get(key)
        if raw is not None:
            digits = re.sub(r"[^\d]", "", str(raw))
            if digits:
                return int(digits)
    blob = norm_text(f"{item.title} {item.description or ''}")
    m = re.search(r"(\d)\s*(?:власник|owner)", blob)
    if m:
        return int(m.group(1))
    if "один власник" in blob or "1 власник" in blob:
        return 1
    return None


def _normalize_engine_litres(raw: float) -> float | None:
    from app.services.listings.engine_volume import normalize_engine_litres

    return normalize_engine_litres(raw)


def extract_listing_engine_volume(item: ListingOut) -> float | None:
    from app.services.listings.engine_volume import extract_listing_engine_volume as _extract

    return _extract(item)


def extract_listing_power_hp(item: ListingOut) -> float | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}

    for source in (auto, specs, sd):
        for key in ("powerHp", "power", "powerInt", "horsePower", "hp"):
            raw = source.get(key)
            if raw is None:
                continue
            if isinstance(raw, (int, float)) and float(raw) > 0:
                return float(raw)
            if isinstance(raw, str):
                match = re.search(r"([\d]+)", raw.replace(" ", ""))
                if match:
                    return float(match.group(1))
        power_block = source.get("power")
        if isinstance(power_block, dict):
            for sub_key in ("hp", "value", "power"):
                sub = power_block.get(sub_key)
                if isinstance(sub, (int, float)) and float(sub) > 0:
                    return float(sub)

    blob = norm_text(f"{item.title} {item.description or ''}")
    match = re.search(r"(\d{2,4})\s*(?:к\.?\s*с\.?|л\.?\s*с\.?|hp|кс)\b", blob, re.I)
    if match:
        return float(match.group(1))
    return None


def extract_listing_body_label(item: ListingOut) -> str | None:
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}

    candidates: list[str] = []
    for source in (auto, sd, specs):
        for key in ("bodyName", "subCategoryName", "subCategoryNameEng", "body", "тип кузова"):
            raw = source.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append(norm_text(raw.strip()))

    for spec_key, spec_value in specs.items():
        if not isinstance(spec_value, str):
            continue
        key = norm_text(str(spec_key))
        if "кузов" in key or "body" in key:
            candidates.append(norm_text(spec_value.strip()))

    for label in candidates:
        if label:
            return label

    blob = norm_text(f"{item.title} {item.description or ''}")
    for canonical, aliases in _BODY_ALIASES.items():
        if canonical in blob or any(alias in blob for alias in aliases):
            return canonical
    return None


def _listing_haystack(item: ListingOut) -> str:
    blob = norm_text(f"{item.title} {item.description or ''} {item.fuel} {item.transmission}")
    sd = item.source_data if isinstance(item.source_data, dict) else {}
    specs = sd.get("specs") if isinstance(sd.get("specs"), dict) else {}
    specs_blob = norm_text(" ".join(str(v) for v in specs.values() if isinstance(v, str)))
    auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
    auto_blob = norm_text(
        " ".join(str(v) for v in auto.values() if isinstance(v, (str, int, float)))
    )
    return f"{blob} {specs_blob} {auto_blob}"


def _body_label_matches(body_name: str, body_labels: list[str]) -> bool:
    body = norm_text(body_name)
    for label in body_labels:
        key = norm_text(label)
        if key in body or body in key:
            return True
        for canonical, aliases in _BODY_ALIASES.items():
            canon = norm_text(canonical)
            filter_is_this_type = key == canon or key in aliases or canon in key
            if not filter_is_this_type:
                continue
            if body == canon or body in aliases or any(alias in body for alias in aliases):
                return True
        if key in BODY_TYPE_TO_ID and key in body:
            return True
    return False


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
        return True
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


def _tri_state_matches(
    mode: str | None,
    *,
    show_tokens: tuple[str, ...],
    hide_tokens: tuple[str, ...],
    haystack: str,
    detected: bool | None,
) -> bool:
    if not mode or mode.strip().lower() in ("", "all"):
        return True
    m = mode.strip().lower()
    if m == "show":
        if detected is True:
            return True
        return any(token in haystack for token in show_tokens)
    if m == "hide":
        if detected is True:
            return False
        if detected is False:
            return True
        return not any(token in haystack for token in show_tokens)
    return True


def listing_matches_advanced_filters(item: ListingOut, filters: SearchFilters) -> bool:
    if not advanced_filters_active(filters):
        return True

    if not listing_matches_seats_filter(item, filters):
        return False

    if filters.doors_from is not None or filters.doors_to is not None:
        doors = extract_listing_doors(item)
        if doors is not None:
            if filters.doors_from is not None and doors < filters.doors_from:
                return False
            if filters.doors_to is not None and doors > filters.doors_to:
                return False

    if filters.body_types:
        body_name = extract_listing_body_label(item)
        if body_name and not _body_label_matches(body_name, filters.body_types):
            return False

    if filters.zero_mileage and item.mileage > 500:
        return False

    if filters.seller_filter and item.seller_type:
        want = filters.seller_filter.strip().lower()
        if want == "private" and item.seller_type != "private":
            return False
        if want == "dealer" and item.seller_type != "dealer":
            return False

    haystack = _listing_haystack(item)

    if filters.accident == "none":
        if re.search(r"\b(дтп|accident|after crash)\b", haystack):
            return False
        sd = item.source_data if isinstance(item.source_data, dict) else {}
        auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
        damage = norm_text(str(auto.get("damageName") or auto.get("damage") or ""))
        if damage and any(x in damage for x in ("був", "after", "після")):
            return False
    elif filters.accident == "had":
        if not re.search(r"\b(дтп|accident|після дтп|був у дтп)\b", haystack):
            sd = item.source_data if isinstance(item.source_data, dict) else {}
            auto = sd.get("autoData") if isinstance(sd.get("autoData"), dict) else {}
            damage = norm_text(str(auto.get("damageName") or ""))
            if "дтп" not in damage and "accident" not in damage:
                return False

    if filters.bargain:
        if "торг" not in haystack and "negotiable" not in haystack:
            return False

    if filters.vin_verified and not item.vin_checked:
        return False

    if filters.owners_max is not None:
        owners = extract_listing_owners(item)
        if owners is not None:
            limit = 4 if filters.owners_max >= 4 else filters.owners_max
            if owners > limit:
                return False

    if filters.in_credit:
        if not _tri_state_matches(
            filters.in_credit,
            show_tokens=("кредит", "застав", "банк", "credit"),
            hide_tokens=(),
            haystack=haystack,
            detected=None,
        ):
            return False

    if filters.usa_import:
        if not _tri_state_matches(
            filters.usa_import,
            show_tokens=("сша", "usa", "america", "штати"),
            hide_tokens=(),
            haystack=haystack,
            detected=None,
        ):
            return False

    if filters.not_customs:
        import_hint = any(
            token in haystack
            for token in ("нерозмит", "під пригон", "пригон", "на брокера", "customs")
        )
        if not _tri_state_matches(
            filters.not_customs,
            show_tokens=("нерозмит", "під пригон", "пригон", "на брокера"),
            hide_tokens=(),
            haystack=haystack,
            detected=import_hint if import_hint else None,
        ):
            return False

    if filters.metallic and "металік" not in haystack and "metallic" not in haystack:
        return False

    if filters.engine_volume_from is not None or filters.engine_volume_to is not None:
        from app.services.listings.engine_volume import listing_engine_volume_in_range

        if not listing_engine_volume_in_range(
            item,
            volume_from=filters.engine_volume_from,
            volume_to=filters.engine_volume_to,
        ):
            return False

    if filters.power_from is not None or filters.power_to is not None:
        power = extract_listing_power_hp(item)
        if power is None:
            power = _spec_number_from_listing(item, "потужність", "power", "к.с", "л.с")
        if power is not None:
            unit = (filters.power_unit or "hp").strip().lower()
            if unit == "kw":
                power = power / 1.341
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
    specs_haystack = f"{blob} {specs_blob}"

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
        if specs_haystack:
            matched = any(
                COLOR_NAME_TO_TOKEN.get(norm_text(c), norm_text(c)) in specs_haystack
                for c in filters.colors
            )
            if not matched:
                return False

    return True


def filter_listings_by_advanced(
    items: list[ListingOut],
    filters: SearchFilters,
) -> list[ListingOut]:
    if not advanced_filters_active(filters):
        return items
    return [item for item in items if listing_matches_advanced_filters(item, filters)]
