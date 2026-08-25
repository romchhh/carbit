from __future__ import annotations

import json

from bs4 import BeautifulSoup


def parse_detail_description(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    for block in soup.select("div.px-4.py-4.text-surface-600"):
        text = block.get_text(" ", strip=True)
        if len(text) >= 40:
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
            if len(description) >= 40:
                return description

    return None
