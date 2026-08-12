"""Аудит точності brand/model матчера на всьому FE-каталозі.

Recall  — заголовок «{Brand} {Model} 2019» має матчити фільтр (Brand, Model).
Precision — заголовок чужої пари не має матчити, окрім свідомо споріднених
(«C-Class» ⊃ «C-Class Coupe», «3 Series» ⊃ «320i» тощо).

Запуск:  PYTHONPATH=..:. python scripts/audit_model_matching.py [--limit N]
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict

from app.core.text import norm_text
from app.services.olx.brand_slugs import resolve_olx_brand_slug
from app.services.search.brand_model_keywords import (
    text_matches_brand_filter,
    text_matches_model_filter,
)
from app.services.search.fe_catalog import load_fe_brand_models

YEAR = "2019"

# Реальні оголошення — це не «Brand Model рік», а текст із ціною, містом,
# пробігом і торгом. Матчер має витримувати цей шум.
TITLE_TEMPLATES = (
    "{brand} {model} {year}",
    "Продам {brand} {model}, {year} р.в., 120 000 км, Київ",
    "{brand} {model} {year} — ідеальний стан, торг при огляді, 18 500$",
    "{model} {year} {brand} офіційний сервіс, один власник",
    "СРОЧНО! {brand} {model}, {year}, розмитнений, обмін",
)


_ACTIVE_TEMPLATES: tuple[str, ...] = TITLE_TEMPLATES


def titles_for(brand: str, model: str) -> list[str]:
    return [
        tpl.format(brand=brand, model=model, year=YEAR) for tpl in _ACTIVE_TEMPLATES
    ]


def title_for(brand: str, model: str) -> str:
    return f"{brand} {model} {YEAR}"


def _same_family(brand_a: str, brand_b: str) -> bool:
    """Суб-бренди: Huawei продає Aito/Luxeed, тож це не чужа марка."""
    a, b = norm_text(brand_a), norm_text(brand_b)
    return a in b or b in a


def _related(model_a: str, model_b: str) -> bool:
    """Моделі свідомо перетинаються — не рахуємо як хибний матч."""
    a, b = norm_text(model_a), norm_text(model_b)
    if not a or not b:
        return True
    if a == b:
        return True
    # «C-Class» vs «C-Class Coupe», «Golf» vs «Golf GTI»
    if a.startswith(b) or b.startswith(a):
        return True
    a_compact = a.replace(" ", "").replace("-", "")
    b_compact = b.replace(" ", "").replace("-", "")
    if a_compact == b_compact:
        return True
    if a_compact.startswith(b_compact) or b_compact.startswith(a_compact):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="обмежити кількість марок")
    parser.add_argument("--others", type=int, default=60, help="скільки чужих пар на модель")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--show", type=int, default=40, help="скільки прикладів друкувати")
    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="перебрати всі пари замість вибірки (без сліпих зон семплінгу)",
    )
    parser.add_argument(
        "--templates", type=int, default=0, help="скільки шаблонів заголовка (0 = усі)"
    )
    args = parser.parse_args()

    global _ACTIVE_TEMPLATES
    if args.templates:
        _ACTIVE_TEMPLATES = TITLE_TEMPLATES[: args.templates]

    rng = random.Random(args.seed)
    catalog = load_fe_brand_models()
    if not catalog:
        print("FE-каталог не знайдено", file=sys.stderr)
        return 2

    brands = sorted(catalog)
    if args.limit:
        brands = brands[: args.limit]

    pairs: list[tuple[str, str]] = []
    for brand in brands:
        for model in catalog[brand]:
            pairs.append((brand, model))

    print(f"Марок: {len(brands)}, пар brand/model: {len(pairs)}")

    missed: list[tuple[str, str, str]] = []
    for brand, model in pairs:
        for title in titles_for(brand, model):
            if not text_matches_model_filter(title, model, brand=brand):
                missed.append((brand, model, title))

    false_pos: list[tuple[str, str, str]] = []
    fp_by_filter: dict[tuple[str, str], int] = defaultdict(int)
    for brand, model in pairs:
        sample = (
            pairs if args.exhaustive else rng.sample(pairs, min(args.others, len(pairs)))
        )
        for other_brand, other_model in sample:
            if resolve_olx_brand_slug(other_brand) == resolve_olx_brand_slug(brand):
                continue
            if _related(model, other_model) or _same_family(brand, other_brand):
                continue
            # Суб-бренд у назві моделі: Huawei «Aito M6» ↔ марка «Aito».
            if _same_family(other_brand, model.split()[0]):
                continue
            if _same_family(brand, other_model.split()[0]):
                continue
            for title in titles_for(other_brand, other_model):
                # Реальний гейт = бренд І модель (як у _title_matches_brand_model).
                if not text_matches_brand_filter(title, brand, model=model):
                    continue
                if text_matches_model_filter(title, model, brand=brand):
                    false_pos.append((brand, model, title))
                    fp_by_filter[(brand, model)] += 1

    print()
    print(f"FALSE NEGATIVES (свою ж модель не впізнав): {len(missed)} / {len(pairs)}")
    for brand, model, title in missed[: args.show]:
        print(f"  фільтр {brand!r}/{model!r}  ←  {title!r}")

    print()
    print(f"FALSE POSITIVES (чуже авто пройшло): {len(false_pos)}")
    worst = sorted(fp_by_filter.items(), key=lambda kv: -kv[1])[: args.show]
    for (brand, model), count in worst:
        examples = [t for b, m, t in false_pos if b == brand and m == model][:3]
        print(f"  {count:4d}×  фільтр {brand!r}/{model!r}")
        for ex in examples:
            print(f"           ← {ex!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
