#!/usr/bin/env python3
"""One-off live check: Mercedes-Benz S-Class, м. Київ → AUTO.RIA search."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# Load .env without echoing secrets
env_path = ROOT / ".env"
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def main() -> int:
    from app.schemas.schemas import SearchFilters
    from app.services.auto_ria.catalog import resolve_mark_id, resolve_model_id
    from app.services.auto_ria.client import AutoRiaClient, AutoRiaError
    from app.services.auto_ria.mapper import filters_to_search_params

    filters = SearchFilters(
        brand="Mercedes-Benz",
        model="S-Class",
        region="м. Київ",
        currency="USD",
    )

    try:
        client = AutoRiaClient()
    except AutoRiaError as exc:
        print(f"FAIL config: {exc}")
        return 1

    mark_id = await resolve_mark_id(client, filters.brand or "")
    model_id = await resolve_model_id(client, mark_id, filters.model or "") if mark_id else None
    print(f"mark_id={mark_id} model_id={model_id}")

    params = await filters_to_search_params(client, filters, page=1, per_page=10)
    interesting = {
        k: params[k]
        for k in sorted(params)
        if any(x in k for x in ("marka", "model", "state", "city", "page", "count"))
    }
    print("search params:", json.dumps(interesting, ensure_ascii=False))

    try:
        data = await client.search(params)
        sr = (data.get("result") or {}).get("search_result") or {}
        count = sr.get("count")
        ids = sr.get("ids") or []
        print(f"OK search: count={count} ids_on_page={len(ids)} sample_ids={ids[:3]}")
    except AutoRiaError as exc:
        print(f"FAIL search: {exc} (status={exc.status_code})")
        return 1

    if ids:
        sample = str(ids[0])
        try:
            info = await client.get_info(sample)
            title = info.get("title") or info.get("markName", "") + " " + str(info.get("modelName", ""))
            print(f"OK info[{sample}]: {title.strip()[:80]}")
        except AutoRiaError as exc:
            print(f"WARN info[{sample}]: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
