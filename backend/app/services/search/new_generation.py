"""Successor names for dealer-new cars (current generation sold under a new badge)."""

from __future__ import annotations

from app.core.text import letter_class_canonical, norm_text

# (brand_slug, model_key) → catalog names to search on AUTO.RIA / uDrive /new.
NEW_GENERATION_MODELS: dict[tuple[str, str], tuple[str, ...]] = {
    # B10 sedan is sold as A5, not A4.
    ("audi", "a4"): ("A4", "A4 Allroad", "A5", "A5 Sportback", "A5L"),
    # Coupe/cabrio successor is CLE; All-Terrain is a separate catalog row.
    ("mercedes-benz", "c-class"): ("C-Class", "C-Class All-Terrain", "CLE-Class", "CLE"),
}


def _brand_key(brand: str) -> str:
    from app.services.olx.brand_slugs import resolve_olx_brand_slug

    slug = resolve_olx_brand_slug(brand) if brand else ""
    return slug or norm_text(brand).replace(" ", "-")


def _model_key(model: str) -> str:
    return letter_class_canonical(model) or norm_text(model)


def new_generation_models(brand: str, model: str) -> tuple[str, ...]:
    """Models that count as the same car in the new-car catalog.

    Used search stays exact (A4 ≠ A5). Empty model → empty tuple.
    """
    model = (model or "").strip()
    if not model:
        return ()
    alts = NEW_GENERATION_MODELS.get((_brand_key(brand), _model_key(model)))
    if alts:
        return alts
    return (model,)
