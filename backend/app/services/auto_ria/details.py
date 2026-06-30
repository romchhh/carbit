from __future__ import annotations

import copy
from typing import Any

from app.services.auto_ria.client import AutoRiaError
from app.services.auto_ria.constants import AUTO_RIA_SITE_URL


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


def _add_image(urls: list[str], seen: set[str], value: Any) -> None:
    if not isinstance(value, str):
        return
    url = value.strip()
    if url.startswith("http") and url not in seen:
        seen.add(url)
        urls.append(url)


def extract_image_urls(info: dict[str, Any], fotos_payload: Any | None = None) -> list[str]:
    auto_data = info.get("autoData") or {}
    auto_id = str(auto_data.get("autoId") or "")
    urls: list[str] = []
    seen: set[str] = set()

    if isinstance(fotos_payload, dict):
        data = fotos_payload.get("data")
        if isinstance(data, dict):
            auto_block = data.get(auto_id) if auto_id in data else None
            if auto_block is None and data:
                auto_block = next(iter(data.values()), None)
            if isinstance(auto_block, dict):
                for photo in auto_block.values():
                    if not isinstance(photo, dict):
                        continue
                    formats = photo.get("formats")
                    if not isinstance(formats, list):
                        continue
                    preferred = next(
                        (item for item in formats if isinstance(item, str) and item.endswith("f.jpg")),
                        None,
                    )
                    _add_image(urls, seen, preferred or (formats[0] if formats else None))

    photo_data = info.get("photoData") or {}
    if isinstance(photo_data, dict):
        for key in ("seoLinkF", "seoLinkM", "seoLinkB", "seoLinkSX"):
            _add_image(urls, seen, photo_data.get(key))
        photo_all = photo_data.get("all")
        if isinstance(photo_all, list):
            for item in photo_all:
                _add_image(urls, seen, item)

    return urls


def sanitize_source_data(info: dict[str, Any], fotos_payload: Any | None = None) -> dict[str, Any]:
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

    return payload
