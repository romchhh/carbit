#!/usr/bin/env python3
"""Minimal live AUTO.RIA check (no FastAPI deps). Mercedes S-Class, Kyiv."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://developers.ria.com"
LANG = 4
MARK_ID = 47  # Mercedes-Benz
MODEL_ID = 906  # S-Класс (typical; verified from /models if needed)
STATE_ID = 10
CITY_ID = 10


def load_api_key() -> str:
    root = Path(__file__).resolve().parents[2]
    key = os.environ.get("AUTO_RIA_API_KEY", "").strip()
    if key:
        return key
    env = root / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("AUTO_RIA_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("FAIL: AUTO_RIA_API_KEY not set")
    sys.exit(1)


def get(path: str, params: dict) -> tuple[int, object]:
    q = urllib.parse.urlencode({**params, "api_key": API_KEY, "lang_id": LANG})
    url = f"{BASE}{path}?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "carbit-live-test/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read(300).decode(errors="replace")
        return exc.code, body


API_KEY = load_api_key()


def resolve_s_class_model_id() -> int:
    status, data = get(
        f"/auto/categories/1/marks/{MARK_ID}/models",
        {},
    )
    if status != 200 or not isinstance(data, list):
        print(f"WARN models list HTTP {status}: {str(data)[:120]}")
        return MODEL_ID
    for item in data:
        name = str(item.get("name", "")).lower()
        if name in ("s-класс", "s-class", "s класс", "s клас"):
            mid = int(item["value"])
            print(f"resolved S-Class model_id={mid} name={item.get('name')!r}")
            return mid
    print("WARN S-Class not found in catalog, using fallback model_id")
    return MODEL_ID


def main() -> int:
    model_id = resolve_s_class_model_id()

    params = {
        "category_id": 1,
        "marka_id[0]": MARK_ID,
        "model_id[0]": model_id,
        "state[0]": STATE_ID,
        "city[0]": CITY_ID,
        "page": 0,
        "countpage": 10,
        "status_id": 0,
        "searchType": 4,
        "currency": 1,
    }
    print("search params:", json.dumps(params, ensure_ascii=False))

    status, data = get("/auto/search", params)
    if status != 200:
        print(f"FAIL search HTTP {status}: {str(data)[:200]}")
        return 1

    sr = ((data if isinstance(data, dict) else {}).get("result") or {}).get("search_result") or {}
    count = sr.get("count")
    ids = sr.get("ids") or []
    print(f"OK search: count={count} ids={len(ids)} sample={ids[:3]}")

    if not ids:
        return 0

    status, info_raw = get("/auto/info", {"auto_id": str(ids[0])})
    if status != 200:
        print(f"WARN info HTTP {status}: {str(info_raw)[:200]}")
        return 0

    if isinstance(info_raw, list) and info_raw:
        row = info_raw[0]
    elif isinstance(info_raw, dict):
        row = info_raw
    else:
        row = {}
    title = row.get("title") or f"{row.get('markName', '')} {row.get('modelName', '')}".strip()
    print(f"OK info[{ids[0]}]: {title[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
