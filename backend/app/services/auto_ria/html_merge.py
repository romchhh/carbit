"""Злиття HTML-картки пошуку з відповіддю платного /auto/info."""

from __future__ import annotations

from typing import Any

from app.schemas.schemas import ListingOut


def listing_numeric_id(listing: ListingOut) -> str | None:
    """Ключ пулу: `12345` вживані, `n:2084935` нові дилерські."""
    lid = (listing.id or "").strip()
    if lid.startswith("new_auto_ria_"):
        suffix = lid.removeprefix("new_auto_ria_")
        return f"n:{suffix}" if suffix.isdigit() else None
    for prefix in ("auto_ria_beta_", "auto_ria_"):
        if lid.startswith(prefix):
            suffix = lid.removeprefix(prefix)
            if suffix.isdigit():
                return suffix
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _merge_flag_maps(api_map: Any, html_map: Any) -> dict[str, Any] | None:
    out = _as_dict(api_map)
    for key, value in _as_dict(html_map).items():
        if value is True:
            out[key] = True
        elif key not in out and value is not None:
            out[key] = value
    return out or None


def _best_published_at(*values: Any) -> Any:
    from app.services.listings.sort_dates import usable_sort_datetime

    for value in values:
        if usable_sort_datetime(value) is not None:
            return value
    for value in values:
        if value is not None:
            return value
    return None


def _first_text(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def merge_html_card_with_api(html: ListingOut, api: ListingOut) -> ListingOut:
    """API — джерело VIN/дат/autoData; HTML заповнює прогалини і True-бейджі з видачі."""
    html_sd = _as_dict(html.source_data)
    api_sd = _as_dict(api.source_data)

    html_search = html_sd.get("html_search") or html_sd.get("auto_ria_beta")
    if html_search:
        api_sd["html_search"] = html_search

    badges = _merge_flag_maps(api_sd.get("ria_page_badges"), html_sd.get("ria_page_badges"))
    if badges:
        api_sd["ria_page_badges"] = badges
    flags = _merge_flag_maps(api_sd.get("condition_flags"), html_sd.get("condition_flags"))
    if flags:
        api_sd["condition_flags"] = flags

    if not api_sd.get("VIN") and html_sd.get("VIN"):
        api_sd["VIN"] = html_sd["VIN"]
    if not api_sd.get("plateNumber") and html_sd.get("plateNumber"):
        api_sd["plateNumber"] = html_sd["plateNumber"]

    html_bar = html_sd.get("autoInfoBar")
    api_bar = api_sd.get("autoInfoBar")
    if isinstance(html_bar, dict):
        merged_bar = _as_dict(api_bar)
        if html_bar.get("damage") is True:
            merged_bar["damage"] = True
        elif "damage" not in merged_bar and html_bar.get("damage") is not None:
            merged_bar["damage"] = html_bar["damage"]
        if merged_bar:
            api_sd["autoInfoBar"] = merged_bar

    images = list(api.images or []) or list(html.images or [])
    payload = api.model_dump(mode="python")
    payload.update(
        images=images,
        vin=_first_text(api.vin, html.vin),
        plate=_first_text(api.plate, html.plate),
        vin_checked=api.vin_checked if api.vin_checked is not None else html.vin_checked,
        vin_check_url=_first_text(api.vin_check_url, html.vin_check_url),
        seller_name=_first_text(api.seller_name, html.seller_name),
        description=_first_text(api.description, html.description),
        engine_volume_l=api.engine_volume_l if api.engine_volume_l is not None else html.engine_volume_l,
        fuel=_first_text(api.fuel, html.fuel) or "",
        transmission=_first_text(api.transmission, html.transmission) or "",
        region=_first_text(api.region, html.region) or "",
        source_data=api_sd,
        published_at=_best_published_at(api.published_at, html.published_at),
        is_new=True if api.is_new or html.is_new else api.is_new,
    )
    return ListingOut.model_validate(payload)
