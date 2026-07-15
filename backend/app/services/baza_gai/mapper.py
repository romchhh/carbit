from __future__ import annotations

from typing import Any

from app.schemas.schemas import VinCheckOperationOut, VinCheckOut, VinStolenDetailOut


def _localized(value: Any, *, prefer_ua: bool = True) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        for key in (("ua", "uk", "ru") if prefer_ua else ("ru", "ua", "uk")):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
        title = value.get("title")
        if isinstance(title, dict):
            return _localized(title, prefer_ua=prefer_ua)
        if isinstance(title, str) and title.strip():
            return title.strip()
    return None


def _region_name(raw: Any) -> str | None:
    if not isinstance(raw, dict):
        return None
    name = raw.get("name_ua") or raw.get("name")
    if isinstance(name, dict):
        return _localized(name)
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def _color_name(raw: Any) -> str | None:
    if isinstance(raw, dict):
        return _localized(raw) or _localized(raw.get("title"))
    if isinstance(raw, str):
        return raw.strip() or None
    return None


def _map_operation(raw: Any) -> VinCheckOperationOut | None:
    if not isinstance(raw, dict):
        return None
    operation = raw.get("operation")
    title = None
    group = None
    if isinstance(operation, dict):
        title = _localized(operation)
        group_raw = operation.get("group")
        if isinstance(group_raw, str):
            group = group_raw
        elif isinstance(raw.get("operation_group"), dict):
            group = _localized(raw.get("operation_group"))
    elif isinstance(operation, str):
        title = operation

    if not group and isinstance(raw.get("operation_group"), dict):
        group = _localized(raw.get("operation_group"))

    return VinCheckOperationOut(
        registered_at=str(raw.get("registered_at") or "").strip() or None,
        digits=str(raw.get("digits") or "").strip() or None,
        model_year=int(raw["model_year"]) if isinstance(raw.get("model_year"), int) else None,
        vendor=str(raw.get("vendor") or "").strip() or None,
        model=str(raw.get("model") or "").strip() or None,
        operation=title,
        operation_group=group,
        department=str(raw.get("department") or "").strip()
        if isinstance(raw.get("department"), str)
        else (
            str((raw.get("department") or {}).get("title") or "").strip() or None
            if isinstance(raw.get("department"), dict)
            else None
        ),
        color=_color_name(raw.get("color")),
        address=str(raw.get("address") or "").strip() or None,
        is_last=bool(raw.get("is_last")) if raw.get("is_last") is not None else None,
    )


def _map_stolen(raw: Any) -> list[VinStolenDetailOut]:
    if not isinstance(raw, list):
        return []
    out: list[VinStolenDetailOut] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            VinStolenDetailOut(
                theft_at=str(item.get("theft_at") or "").strip() or None,
                vendor_title=str(item.get("vendor_title") or "").strip() or None,
                car_type=str(item.get("car_type") or "").strip() or None,
                chassis_number=str(item.get("chassis_number") or "").strip() or None,
                department_title=str(item.get("department_title") or "").strip() or None,
                color=_color_name(item.get("color")) or str(item.get("raw_color") or "").strip() or None,
            )
        )
    return out


def map_vin_payload(raw: dict[str, Any], *, vin: str) -> VinCheckOut:
    operations_raw = raw.get("operations") if isinstance(raw.get("operations"), list) else []
    operations: list[VinCheckOperationOut] = []
    for item in operations_raw[:8]:
        mapped = _map_operation(item)
        if mapped:
            operations.append(mapped)

    digits = str(raw.get("digits") or "").strip() or None
    if not digits and operations:
        digits = operations[0].digits

    model_year = raw.get("model_year")
    year = int(model_year) if isinstance(model_year, int) else None

    return VinCheckOut(
        vin=vin.upper(),
        digits=digits,
        vendor=str(raw.get("vendor") or "").strip() or None,
        model=str(raw.get("model") or "").strip() or None,
        model_year=year,
        region=_region_name(raw.get("region")),
        photo_url=str(raw.get("photo_url") or "").strip() or None,
        is_stolen=bool(raw.get("is_stolen")) if raw.get("is_stolen") is not None else False,
        stolen_details=_map_stolen(raw.get("stolen_details")),
        operations=operations,
        source_url=f"https://baza-gai.com.ua/vin/{vin.upper()}",
        from_cache=False,
    )
