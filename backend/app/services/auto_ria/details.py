from __future__ import annotations

import copy
import re
from typing import Any

from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.constants import AUTO_RIA_SITE_URL

# Унікальний id фото в URL CDN (181949196 з ...181949196f.jpg або .../187203123f.jpg)
_PHOTO_ID_RE = re.compile(r"(\d+)(?:[a-z]{1,2})?\.jpg(?:\?.*)?$", re.I)


def normalize_info_response(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        if not data:
            raise AutoRiaError("AUTO.RIA повернув порожню відповідь info")
        first = data[0]
        if isinstance(first, dict):
            return first
        raise AutoRiaError("AUTO.RIA info: неочікуваний елемент масиву")

    if isinstance(data, dict):
        return data

    raise AutoRiaError("AUTO.RIA info: неочікуваний формат відповіді")


def _photo_dedupe_key(url: str) -> str:
    match = _PHOTO_ID_RE.search(url.strip())
    if match:
        return match.group(1)
    return url.strip()


def _add_image(urls: list[str], seen: set[str], value: Any) -> None:
    if not isinstance(value, str):
        return
    url = value.strip()
    if not url.startswith("http"):
        return
    key = _photo_dedupe_key(url)
    if key in seen:
        return
    seen.add(key)
    urls.append(url)


def _format_urls(formats: Any) -> list[str]:
    if isinstance(formats, list):
        return [item for item in formats if isinstance(item, str)]
    if isinstance(formats, dict):
        return [item for item in formats.values() if isinstance(item, str)]
    return []


def _pick_best_format_url(formats: Any) -> str | None:
    candidates = _format_urls(formats)
    if not candidates:
        return None

    for url in candidates:
        if url.endswith("f.jpg") and not url.endswith("fx.jpg"):
            return url

    for suffix in ("fx.jpg", "b.jpg", "m.jpg", "sx.jpg"):
        for url in candidates:
            if url.endswith(suffix):
                return url

    return candidates[0]


def _extract_from_fotos_payload(fotos_payload: dict[str, Any], auto_id: str) -> list[str]:
    data = fotos_payload.get("data")
    if not isinstance(data, dict):
        return []

    auto_block = data.get(auto_id) if auto_id in data else None
    if auto_block is None and data:
        auto_block = next(iter(data.values()), None)
    if not isinstance(auto_block, dict):
        return []

    photos: list[tuple[int, str]] = []
    for raw_id, photo in auto_block.items():
        if not isinstance(photo, dict):
            continue
        url = _pick_best_format_url(photo.get("formats"))
        if not url:
            continue
        photo_id = photo.get("photo_id")
        sort_key = int(photo_id) if isinstance(photo_id, int) else int(raw_id) if str(raw_id).isdigit() else len(photos)
        photos.append((sort_key, url))

    photos.sort(key=lambda item: item[0])

    urls: list[str] = []
    seen: set[str] = set()
    for _, url in photos:
        _add_image(urls, seen, url)
    return urls


def _extract_cover_from_photo_data(photo_data: dict[str, Any]) -> str | None:
    for key in ("seoLinkF", "seoLinkB", "seoLinkM", "seoLinkSX"):
        url = photo_data.get(key)
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None


def extract_image_urls(info: dict[str, Any], fotos_payload: Any | None = None) -> list[str]:
    auto_data = info.get("autoData") or {}
    auto_id = str(auto_data.get("autoId") or "")

    if isinstance(fotos_payload, dict):
        from_fotos = _extract_from_fotos_payload(fotos_payload, auto_id)
        if from_fotos:
            return from_fotos

    photo_data = info.get("photoData") or {}
    if isinstance(photo_data, dict):
        cover = _extract_cover_from_photo_data(photo_data)
        if cover:
            return [cover]

    return []


def sanitize_source_data(info: dict[str, Any], fotos_payload: Any | None = None) -> dict[str, Any]:
    del fotos_payload  # images already extracted separately; raw fotos can break JSON
    payload = copy.deepcopy(info)

    link = str(payload.get("linkToView") or "").strip()
    if link and not link.startswith("http"):
        payload["linkToView"] = f"{AUTO_RIA_SITE_URL}{link}"

    checked = payload.get("checkedVin")
    if isinstance(checked, dict):
        report = str(checked.get("linkToReport") or "").strip()
        if report and not report.startswith("http"):
            checked["linkToReport"] = f"{AUTO_RIA_SITE_URL}{report}"

    dealer = payload.get("dealer")
    if isinstance(dealer, dict):
        dealer_link = str(dealer.get("link") or "").strip()
        if dealer_link and not dealer_link.startswith("http"):
            dealer["link"] = f"{AUTO_RIA_SITE_URL}{dealer_link}"

    payload.pop("vinSvg", None)
    # Не кладемо сирий fotos у відповідь API — images уже зібрані окремо,
    # а великий вкладений об'єкт інколи ламає JSON-серіалізацію (500).
    payload.pop("_fotos", None)

    from app.services.listings.sanitize import json_safe

    return json_safe(payload) if isinstance(payload, dict) else {}
