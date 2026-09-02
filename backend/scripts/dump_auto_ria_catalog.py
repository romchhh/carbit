#!/usr/bin/env python3
"""One-shot dump of AUTO.RIA marks/models for FE filter brands → static JSON.

Usage (from repo root):
  python backend/scripts/dump_auto_ria_catalog.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.text import norm_text  # noqa: E402
from app.services.search.fe_catalog import load_fe_brand_models  # noqa: E402

BASE = "https://developers.ria.com"
LANG_ID = 4
OUT_PATH = ROOT / "backend" / "app" / "services" / "auto_ria" / "ria_id_catalog.json"

# FE label → extra AUTO.RIA mark names (uk/ru/en).
_MARK_ALIASES: dict[str, tuple[str, ...]] = {
    "Lada": ("vaz", "ваз", "лада", "lada"),
    "Mercedes-Benz": ("mercedes-benz", "mercedes", "мерседес", "mercedes benz"),
    "Land Rover": ("land rover", "ленд ровер", "land-rover"),
    "Alfa Romeo": ("alfa romeo", "альфа ромео"),
    "Great Wall": ("great wall", "gwm", "грейт вол"),
    "Li Auto": ("li auto", "li-auto", "lixiang", "лисян"),
    "Lynk & Co": ("lynk & co", "lynk&co", "lynk and co"),
    "SsangYong": ("ssangyong", "ssangyong", "санъенг", "sang yong"),
    "Citroen": ("citroen", "citroën", "сітроен"),
    "Skoda": ("skoda", "škoda", "шкода"),
    "Volkswagen": ("volkswagen", "vw", "фольксваген"),
    "ZAZ": ("zaz", "заз"),
    "Infiniti": ("infiniti", "infinity"),
    "EXEED": ("exeed",),
    "Chery": ("chery", "чері", "чери"),
    "GWM": ("gwm",),
}


def _load_api_key() -> str:
    key = os.environ.get("AUTO_RIA_API_KEY", "").strip()
    if key:
        return key
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("AUTO_RIA_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("AUTO_RIA_API_KEY not set")


def _get(api_key: str, path: str) -> object:
    q = urllib.parse.urlencode({"api_key": api_key, "lang_id": LANG_ID})
    url = f"{BASE}{path}?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "carbit-catalog-dump/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _alias_keys(brand: str) -> set[str]:
    keys = {norm_text(brand)}
    for extra in _MARK_ALIASES.get(brand, ()):
        keys.add(norm_text(extra))
    return {k for k in keys if k}


def main() -> int:
    api_key = _load_api_key()
    fe = load_fe_brand_models()
    print(f"FE brands: {len(fe)}", flush=True)

    marks_raw = _get(api_key, "/auto/categories/1/marks")
    if not isinstance(marks_raw, list):
        raise SystemExit(f"unexpected marks payload: {type(marks_raw)}")
    marks = [
        {"name": str(item.get("name", "")).strip(), "value": int(item["value"])}
        for item in marks_raw
        if item.get("name") is not None and item.get("value") is not None
    ]
    print(f"AUTO.RIA marks: {len(marks)}", flush=True)

    by_norm: dict[str, dict] = {}
    for item in marks:
        key = norm_text(item["name"])
        if key:
            by_norm.setdefault(key, item)

    wanted: dict[int, str] = {}
    missing_brands: list[str] = []
    for brand in fe:
        hit = None
        for key in _alias_keys(brand):
            if key in by_norm:
                hit = by_norm[key]
                break
        if hit is None:
            for key in _alias_keys(brand):
                for n, item in by_norm.items():
                    if key in n or n in key:
                        hit = item
                        break
                if hit is not None:
                    break
        if hit is None:
            missing_brands.append(brand)
            continue
        wanted[int(hit["value"])] = brand

    print(f"matched marks: {len(wanted)}; missing: {missing_brands}", flush=True)

    models: dict[str, list[dict]] = {}
    for i, (mark_id, brand) in enumerate(sorted(wanted.items(), key=lambda kv: kv[1].lower()), start=1):
        path = f"/auto/categories/1/marks/{mark_id}/models"
        try:
            data = _get(api_key, path)
        except Exception as exc:
            print(f"FAIL models mark={mark_id} brand={brand}: {exc}", flush=True)
            continue
        if not isinstance(data, list):
            print(f"WARN models mark={mark_id} brand={brand}: {type(data)}", flush=True)
            continue
        rows = [
            {"name": str(item.get("name", "")).strip(), "value": int(item["value"])}
            for item in data
            if item.get("name") is not None and item.get("value") is not None
        ]
        models[str(mark_id)] = rows
        print(f"[{i}/{len(wanted)}] {brand} id={mark_id} models={len(rows)}", flush=True)
        time.sleep(0.15)

    payload = {
        "category_id": 1,
        "lang_id": LANG_ID,
        "marks": marks,
        "models": models,
        "fe_mark_ids": {brand: mark_id for mark_id, brand in wanted.items()},
        "missing_fe_brands": missing_brands,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH} marks={len(marks)} model_groups={len(models)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
