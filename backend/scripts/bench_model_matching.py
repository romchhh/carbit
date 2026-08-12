"""Бенчмарк гарячого шляху фільтрації: N оголошень × brand/model фільтр.

Запуск: PYTHONPATH=..:. python scripts/bench_model_matching.py [--listings N]
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import random
import time

from app.services.search.brand_model_keywords import (
    text_matches_brand_filter,
    text_matches_model_filter,
)
from app.services.search.fe_catalog import load_fe_brand_models

TEMPLATES = (
    "{brand} {model} 2019",
    "Продам {brand} {model}, 2018 р.в., 120 000 км, Київ. Терміново, торг",
    "{brand} {model} 2020 — офіційний сервіс, один власник, 24 900$",
)


def build_listings(count: int, seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    catalog = load_fe_brand_models()
    pairs = [(b, m) for b, models in catalog.items() for m in models]
    out = []
    for _ in range(count):
        brand, model = rng.choice(pairs)
        out.append(rng.choice(TEMPLATES).format(brand=brand, model=model))
    return out


FILTERS = (
    ("Mercedes-Benz", "S-Class"),
    ("BMW", "7 Series"),
    ("Toyota", "Camry"),
    ("Volkswagen", "Golf"),
    ("Audi", "Q7"),
)


def run(listings: list[str]) -> int:
    hits = 0
    for brand, model in FILTERS:
        for title in listings:
            if not text_matches_brand_filter(title, brand, model=model):
                continue
            if text_matches_model_filter(title, model, brand=brand):
                hits += 1
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings", type=int, default=500)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--profile", action="store_true")
    args = ap.parse_args()

    listings = build_listings(args.listings)
    run(listings[:20])  # прогрів кешів

    if args.profile:
        prof = cProfile.Profile()
        prof.enable()
        run(listings)
        prof.disable()
        pstats.Stats(prof).sort_stats("cumulative").print_stats(22)
        return 0

    best = None
    for _ in range(args.repeat):
        start = time.perf_counter()
        hits = run(listings)
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)

    checks = len(listings) * len(FILTERS)
    print(f"оголошень: {len(listings)}, фільтрів: {len(FILTERS)}, перевірок: {checks}")
    print(f"збігів: {hits}")
    print(f"час: {best * 1000:.1f} ms  ({best / checks * 1e6:.1f} мкс на перевірку)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
