from __future__ import annotations

import json

from bs4 import BeautifulSoup
from datetime import datetime

from app.services.listings.plate import normalize_ua_plate
from app.services.reono.dates import parse_reono_updated_text


def parse_detail_plate(html: str) -> str | None:
    """Держномер з блоку перевірки МВС на сторінці оголошення."""
    soup = BeautifulSoup(html, "html.parser")
    number_el = soup.select_one(".characteristecs-car-main__body__info__number__country__number")
    if number_el is not None:
        plate = normalize_ua_plate(number_el.get_text(" ", strip=True))
        if plate:
            return plate

    block_el = soup.select_one(".characteristecs-car-main__body__info__number")
    if block_el is not None:
        text = block_el.get_text(" ", strip=True)
        if text.upper().startswith("UA "):
            text = text[3:].strip()
        plate = normalize_ua_plate(text)
        if plate:
            return plate
    return None


def parse_detail_description(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    content = soup.select_one(".about-car-main__content")
    if content is not None:
        text = content.get_text(" ", strip=True)
        if text:
            return text

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Car":
            description = str(data.get("description") or "").strip()
            if description:
                return description

    return None


def parse_detail_published_at(html: str) -> datetime | None:
    """Дата оновлення оголошення на REONO (блок МВС «Оновлено …»)."""
    soup = BeautifulSoup(html, "html.parser")
    date_el = soup.select_one(".characteristecs-car-main__body__info__mvs__date")
    if date_el is not None:
        parsed = parse_reono_updated_text(date_el.get_text(" ", strip=True))
        if parsed is not None:
            return parsed
    return parse_reono_updated_text(soup.get_text(" ", strip=True))
