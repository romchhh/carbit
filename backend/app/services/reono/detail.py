from __future__ import annotations

import json

from bs4 import BeautifulSoup
from datetime import datetime

from app.services.reono.dates import parse_reono_updated_text


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
