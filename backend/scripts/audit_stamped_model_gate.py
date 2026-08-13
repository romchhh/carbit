"""Аудит воріт фільтра для проштампованої моделі.

Джерела (OLX / AUTO.RIA) інколи кладуть у поле «model» саме те, що просив
фільтр, навіть коли заголовок описує іншу модель тієї ж марки. Тоді запит
«BMW 5 Series» повертав «BMW X5». Тут перебираємо весь FE-каталог:

  item.model = A (як просив фільтр), заголовок = «<марка> B <рік>»
  фільтр     = марка + A          →  оголошення має бути відкинуте

Плюс контрольний випадок: заголовок з тією ж моделлю A має проходити.

    PYTHONPATH=..:. python scripts/audit_stamped_model_gate.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.schemas.schemas import ListingOut, SearchFilters  # noqa: E402
from app.services.search.fe_catalog import load_fe_brand_models  # noqa: E402
from app.services.telegram_channels.mapper import listing_out_matches_filters  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc)


def make_listing(source: str, brand: str, model: str, title: str) -> ListingOut:
    return ListingOut(
        id=f"{source}_{abs(hash(title)) % 100000}",
        source=source,
        title=title,
        brand=brand,
        model=model,
        year=2020,
        price=25000,
        currency="USD",
        mileage=90000,
        region="м. Київ",
        url="https://example.com/x",
        images=[],
        description=title,
        published_at=NOW,
        found_at=NOW,
        price_history=[],
        is_duplicate=False,
        fuel="Бензин",
        transmission="Автомат",
        seller_type="private",
    )


def accepts(source: str, brand: str, stamped_model: str, title: str, filter_model: str) -> bool:
    item = make_listing(source, brand, stamped_model, title)
    filters = SearchFilters.model_validate({"brand": brand, "model": filter_model})
    return listing_out_matches_filters(item, filters)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--others", type=int, default=3, help="скільки чужих моделей на пару")
    ap.add_argument("--seed", type=int, default=20260813)
    ap.add_argument("--show", type=int, default=25)
    ap.add_argument("--source", default="olx", help="джерело оголошення")
    args = ap.parse_args()

    rnd = random.Random(args.seed)
    catalog = load_fe_brand_models()

    false_positives: list[str] = []
    false_negatives: list[str] = []
    checks = 0

    for brand, models in sorted(catalog.items()):
        models = [m for m in models if str(m).strip()]
        if len(models) < 2:
            continue
        for target in models:
            # контроль: заголовок із тією ж моделлю має проходити
            checks += 1
            if not accepts(args.source, brand, target, f"{brand} {target} 2020", target):
                false_negatives.append(f"{brand} | {target} | заголовок «{brand} {target} 2020»")

            pool = [m for m in models if m != target]
            for other in rnd.sample(pool, min(args.others, len(pool))):
                checks += 1
                # модель проштампована з фільтра, заголовок каже інше
                if accepts(args.source, brand, target, f"{brand} {other} 2020", target):
                    false_positives.append(
                        f"{brand} | фільтр «{target}» | заголовок «{brand} {other} 2020»"
                    )

    print(f"Перевірок: {checks}, марок: {len(catalog)}")
    print(f"\nFALSE NEGATIVES (своє ж не пройшло): {len(false_negatives)}")
    for row in false_negatives[: args.show]:
        print(f"   {row}")
    print(f"\nFALSE POSITIVES (чуже пройшло): {len(false_positives)}")
    for row in false_positives[: args.show]:
        print(f"   {row}")
    return 1 if false_positives or false_negatives else 0


if __name__ == "__main__":
    raise SystemExit(main())
