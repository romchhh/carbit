#!/usr/bin/env python3
"""Audit FE catalog resolution for Imperiya (live API) and OLX (params + optional live)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.schemas import SearchFilters
from app.services.imperiya.catalog import resolve_make_id, resolve_model_id
from app.services.imperiya.client import ImperiyaClient, ImperiyaError
from app.services.olx.brand_slugs import (
    brand_model_forces_text_search,
    brand_uses_olx_text_search,
    compose_olx_text_query,
    resolve_olx_brand_slug,
    resolve_olx_model_slug,
)
from app.services.olx.mapper import filters_to_olx_params
from app.services.search.fe_catalog import load_fe_brand_models
from app.services.search.subbrand_split import split_huawei_subbrand


def audit_olx_static() -> tuple[list[str], list[tuple[str, str, str]]]:
    """Returns (missing_brands, uncovered_models)."""
    catalog = load_fe_brand_models()
    missing_brands: list[str] = []
    uncovered: list[tuple[str, str, str]] = []

    for brand in catalog:
        slug = resolve_olx_brand_slug(brand)
        if not slug:
            missing_brands.append(brand)

    from app.services.olx.olx_model_catalog import (
        OLX_EMPTY_MODEL_TAXONOMY_BRANDS,
        OLX_FE_MODEL_REMAP,
        OLX_KNOWN_MODEL_PATHS,
    )

    for brand, models in catalog.items():
        if brand_uses_olx_text_search(brand):
            continue
        bslug = resolve_olx_brand_slug(brand)
        for model in models:
            if brand_model_forces_text_search(brand, model):
                params = filters_to_olx_params(
                    SearchFilters(brand=brand, model=model, currency="USD")
                )
                if not params.text_query:
                    uncovered.append((brand, model, "no-text-query"))
                continue
            params = filters_to_olx_params(
                SearchFilters(brand=brand, model=model, currency="USD")
            )
            if params.text_query:
                uncovered.append((brand, model, f"unexpected-text:{params.text_query}"))
                continue
            slug = resolve_olx_model_slug(model, brand=brand)
            known = OLX_KNOWN_MODEL_PATHS.get(bslug, frozenset())
            if bslug in OLX_EMPTY_MODEL_TAXONOMY_BRANDS:
                uncovered.append((brand, model, "empty-taxonomy-not-forced"))
                continue
            if slug not in known and f"{bslug}|{model.lower()}" not in OLX_FE_MODEL_REMAP:
                uncovered.append((brand, model, slug or "no-slug"))
    return missing_brands, uncovered


async def audit_imperiya() -> tuple[list[str], list[tuple[str, str]]]:
    """Returns (missing_brands, missing_models)."""
    client = ImperiyaClient()
    catalog = load_fe_brand_models()
    missing_brands: list[str] = []
    missing_models: list[tuple[str, str]] = []

    for brand, models in catalog.items():
        for model in models:
            eff_brand, eff_model = split_huawei_subbrand(brand, model)
            make_id = await resolve_make_id(client, eff_brand)
            if make_id is None:
                if brand not in missing_brands:
                    missing_brands.append(brand)
                continue
            model_id = await resolve_model_id(client, make_id, eff_model, brand=eff_brand)
            if model_id is None:
                missing_models.append((brand, model))
    return missing_brands, missing_models


async def live_sample_search(
    *,
    olx: bool,
    imperiya: bool,
    samples: list[tuple[str, str]],
) -> list[str]:
    errors: list[str] = []

    if imperiya:
        from app.services.imperiya.service import search_imperiya

        for brand, model in samples:
            try:
                r = await search_imperiya(
                    SearchFilters(brand=brand, model=model, sources=["imperiya"]),
                    page=1,
                    per_page=5,
                    use_cache=False,
                )
                status = f"ok total={r.total} items={len(r.items)}"
                if r.total == 0:
                    status = "EMPTY (0 results)"
                print(f"  Imperiya {brand} {model}: {status}")
            except Exception as exc:
                msg = f"Imperiya {brand} {model}: ERROR {exc}"
                print(f"  {msg}")
                errors.append(msg)

    if olx:
        from app.services.olx.service import search_olx

        for brand, model in samples:
            try:
                r = await search_olx(
                    SearchFilters(brand=brand, model=model, sources=["olx"]),
                    page=1,
                    per_page=5,
                    use_cache=False,
                )
                status = f"ok total={r.total} items={len(r.items)}"
                if r.total == 0:
                    status = "EMPTY (0 results)"
                print(f"  OLX {brand} {model}: {status}")
            except Exception as exc:
                msg = f"OLX {brand} {model}: ERROR {exc}"
                print(f"  {msg}")
                errors.append(msg)

    return errors


async def _run_all(args: argparse.Namespace) -> int:
    catalog = load_fe_brand_models()
    brand_count = len(catalog)
    model_count = sum(len(m) for m in catalog.values())
    print(f"FE catalog: {brand_count} brands, {model_count} models\n")

    exit_code = 0

    if not args.imperiya_only:
        print("=== OLX static audit ===")
        missing_brands, uncovered = audit_olx_static()
        print(f"Missing brand slugs: {len(missing_brands)}")
        if missing_brands:
            print(" ", missing_brands[:15])
            exit_code = 1
        print(f"Uncovered path models: {len(uncovered)}")
        if uncovered:
            for row in uncovered[:30]:
                print(f"  {row[0]} / {row[1]} → {row[2]}")
            if len(uncovered) > 30:
                print(f"  ... and {len(uncovered) - 30} more")
            exit_code = 1
        else:
            print("  All FE models have path or text-search coverage.")
        print()

    if not args.olx_only:
        print("=== Imperiya catalog audit (live API) ===")
        try:
            missing_brands, missing_models = await audit_imperiya()
        except ImperiyaError as exc:
            print(f"SKIP: {exc}")
            missing_brands, missing_models = [], []
            exit_code = 1
        else:
            print(f"Missing brands: {len(missing_brands)}")
            if missing_brands:
                print(" ", missing_brands)
            print(f"Unresolved models (fallback to makeId + post-filter): {len(missing_models)}")
            if missing_models:
                for brand, model in missing_models[:40]:
                    print(f"  {brand} / {model}")
                if len(missing_models) > 40:
                    print(f"  ... and {len(missing_models) - 40} more")
        print()

    if args.live:
        samples = [
            ("Zeekr", "001"),
            ("Huawei", "Aito M5"),
            ("Mercedes-Benz", "S-Class"),
            ("Mercedes-Benz", "GLA"),
            ("BMW", "3 Series"),
            ("BMW", "X5"),
            ("Audi", "A4"),
            ("Audi", "Q5"),
            ("Toyota", "Camry"),
            ("Toyota", "RAV4"),
            ("Volkswagen", "Passat"),
            ("Tesla", "Model 3"),
            ("BYD", "Song Plus"),
            ("Haval", "H6"),
            ("NIO", "ET5"),
            ("Porsche", "911"),
            ("Lexus", "RX"),
            ("Volvo", "XC90"),
            ("Renault", "Megane"),
            ("Skoda", "Octavia"),
            ("Ford", "Focus"),
            ("DAF", "XF"),
        ]
        print("=== Live search samples ===")
        run_imperiya = not args.olx_only
        run_olx = not args.imperiya_only
        errors = await live_sample_search(olx=run_olx, imperiya=run_imperiya, samples=samples)
        if errors:
            exit_code = 1
            print(f"\nLive errors: {len(errors)}")

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Run live search samples")
    parser.add_argument("--imperiya-only", action="store_true")
    parser.add_argument("--olx-only", action="store_true")
    args = parser.parse_args()
    return asyncio.run(_run_all(args))
if __name__ == "__main__":
    raise SystemExit(main())
