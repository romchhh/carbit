"""Ensure FE catalog + alias keys stay in sync for search resolution."""

from __future__ import annotations

from app.core.text import norm_text
from app.services.olx.brand_slugs import resolve_olx_brand_slug
from app.services.search.brand_model_keywords import (
    BRAND_SLUG_EXTRA_ALIASES,
    MODEL_EXTRA_ALIASES,
)
from app.services.search.fe_catalog import load_fe_brand_models


def test_every_brand_slug_alias_resolves_to_fe_catalog():
    catalog = load_fe_brand_models()
    labels_by_slug = {resolve_olx_brand_slug(b): b for b in catalog}
    missing = [slug for slug in BRAND_SLUG_EXTRA_ALIASES if slug not in labels_by_slug]
    assert not missing, f"Brand slugs without FE catalog entry: {missing}"


def test_every_model_alias_key_matches_fe_catalog():
    catalog = load_fe_brand_models()
    model_index = {norm_text(m): (brand, m) for brand, models in catalog.items() for m in models}
    missing = [key for key in MODEL_EXTRA_ALIASES if norm_text(key) not in model_index]
    assert not missing, f"Model alias keys without FE catalog match: {missing[:20]}"
