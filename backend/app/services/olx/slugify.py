from __future__ import annotations

from app.services.olx.brand_slugs import resolve_olx_brand_slug, resolve_olx_model_slug, _norm
from app.services.olx.constants import MODEL_SLUG_ALIASES


def brand_slug(brand: str) -> str:
    return resolve_olx_brand_slug(brand)


def model_slug(model: str, *, brand: str = "") -> str:
    key = _norm(model)
    if key in MODEL_SLUG_ALIASES:
        return MODEL_SLUG_ALIASES[key]
    return resolve_olx_model_slug(model, brand=brand)
