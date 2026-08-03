#!/usr/bin/env python3
"""Експорт UA/RU аліасів марок і моделей з бекенду у frontend JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.search.brand_model_keywords import (  # noqa: E402
    BRAND_SLUG_EXTRA_ALIASES,
    MODEL_EXTRA_ALIASES,
)

OUT = ROOT / "frontend/src/lib/search-data/brand-model-aliases.json"


def main() -> None:
    payload = {
        "brandSlugs": {k: list(v) for k, v in BRAND_SLUG_EXTRA_ALIASES.items()},
        "models": {k: list(v) for k, v in MODEL_EXTRA_ALIASES.items()},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} ({len(payload['brandSlugs'])} brands, {len(payload['models'])} model keys)")


if __name__ == "__main__":
    main()
