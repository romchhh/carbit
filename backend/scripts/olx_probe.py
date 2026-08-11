#!/usr/bin/env python3
"""Діагностика OLX з сервера: docker compose exec backend python backend/scripts/olx_probe.py"""
from __future__ import annotations

import asyncio
import sys

from app.services.olx.client import OlxClient
from app.services.olx.transport import CURL_CFFI_AVAILABLE, system_curl_get, transport_summary
from app.core.config import settings


async def main() -> int:
    url = "https://www.olx.ua/uk/transport/legkovye-avtomobili/"
    print("=== OLX probe ===")
    print(transport_summary(
        impersonate=settings.OLX_IMPERSONATE or "chrome136",
        proxy=(settings.OLX_PROXY_URL or "").strip() or None,
    ))
    print("curl_cffi installed:", CURL_CFFI_AVAILABLE)

    headers = {
        "Accept-Language": "uk-UA,uk;q=0.9",
        "Accept": "text/html,*/*",
        "Referer": "https://www.olx.ua/",
    }

    try:
        r = await system_curl_get(url, headers=headers, proxy=(settings.OLX_PROXY_URL or "").strip() or None)
        print("system curl:", r.status_code, "bytes", len(r.text))
    except Exception as exc:
        print("system curl ERROR:", exc)

    try:
        async with OlxClient() as client:
            html = await client.fetch_html(url)
            print("OlxClient OK:", len(html), "transport=", client._transport_label)
    except Exception as exc:
        print("OlxClient ERROR:", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
