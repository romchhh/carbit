from __future__ import annotations

import json

from bs4 import BeautifulSoup


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
