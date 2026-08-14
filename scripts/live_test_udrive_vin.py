"""Live smoke tests: uDrive search + VIN check (Baza GAI + auction)."""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.schemas import SearchFilters
from app.services.baza_gai.service import lookup_vin_check, normalize_vin
from app.services.udrive.service import search_udrive


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


async def test_udrive() -> bool:
    section("uDrive search: Audi A5")
    filters = SearchFilters(
        brand="Audi",
        model="A5",
        sources=["udrive"],
        currency="USD",
    )
    try:
        result = await search_udrive(filters, page=1, per_page=10, sort_by="newest", use_cache=False)
    except Exception as exc:
        print(f"FAIL: search_udrive raised: {exc}")
        traceback.print_exc()
        return False

    print(f"total={result.total} page_items={len(result.items)} pages={result.pages}")
    if not result.items:
        print("FAIL: empty result for Audi A5")
        return False

    ok = True
    for i, item in enumerate(result.items[:5], 1):
        print(
            f"  {i}. [{item.id}] {item.title} | {item.year} | "
            f"{item.price} {item.currency} | {item.region} | photos={len(item.images)}"
        )
        if not item.id.startswith("udrive_"):
            print(f"     FAIL: bad id prefix: {item.id}")
            ok = False
        if item.source != "udrive":
            print(f"     FAIL: bad source: {item.source}")
            ok = False
        if not item.url or "udrive.com.ua" not in item.url:
            print(f"     FAIL: bad url: {item.url}")
            ok = False
        if item.price <= 0:
            print(f"     WARN: price={item.price}")

    first = result.items[0]
    print(f"\nfirst url: {first.url}")
    print(f"first fuel/trans: {first.fuel} / {first.transmission}")
    if first.images:
        print(f"first photo: {first.images[0][:100]}...")
    print("PASS" if ok else "FAIL")
    return ok


async def test_vin() -> bool:
    # Known sample from Baza GAI tests + auction script default
    vins = [
        "WBA7B41080G157838",  # Baza sample (likely in UA registry)
        "5N1AT2MV9JC767550",  # vintest.py default (auction)
    ]
    section("VIN check")
    any_ok = False
    details = []

    for vin_raw in vins:
        vin = normalize_vin(vin_raw)
        print(f"\n--- VIN {vin_raw} (normalized={vin}) ---")
        if not vin:
            print("FAIL: invalid vin")
            continue
        try:
            out = await lookup_vin_check(vin)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            details.append({"vin": vin, "error": str(exc)})
            continue

        summary = {
            "vin": out.vin,
            "vendor": out.vendor,
            "model": out.model,
            "plate": out.plate,
            "is_stolen": out.is_stolen,
            "registrations": out.registrations_count,
            "source_url": out.source_url,
            "has_auction": out.auction is not None,
            "auction_title": out.auction.title if out.auction else None,
            "auction_damage": out.auction.primary_damage if out.auction else None,
            "auction_url": out.auction.page_url if out.auction else None,
            "note": out.note,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        details.append(summary)
        any_ok = True

    print("\nPASS (at least one VIN returned data)" if any_ok else "FAIL (no VIN returned)")
    return any_ok


async def main() -> int:
    udrive_ok = await test_udrive()
    vin_ok = await test_vin()
    section("SUMMARY")
    print(f"uDrive: {'PASS' if udrive_ok else 'FAIL'}")
    print(f"VIN:    {'PASS' if vin_ok else 'FAIL'}")
    return 0 if (udrive_ok and vin_ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
