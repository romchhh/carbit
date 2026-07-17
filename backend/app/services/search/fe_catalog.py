"""FE-каталог марок/моделей (brands-models.ts) для matching усіх брендів."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.core.config import ROOT_DIR
from app.core.text import norm_text
from app.services.olx.brand_slugs import resolve_olx_brand_slug

_FE_CATALOG_PATH = (
    ROOT_DIR / "frontend" / "src" / "lib" / "search-data" / "brands-models.ts"
)


@lru_cache(maxsize=1)
def load_fe_brand_models() -> dict[str, tuple[str, ...]]:
    """brand label → моделі з FE."""
    if not _FE_CATALOG_PATH.is_file():
        return {}
    text = _FE_CATALOG_PATH.read_text(encoding="utf-8")
    out: dict[str, tuple[str, ...]] = {}
    for m in re.finditer(
        r'(?:^|\n)\s*(?:"([^"]+)"|([A-Za-z0-9&]+))\s*:\s*\[([^\]]+)\]',
        text,
    ):
        brand = (m.group(1) or m.group(2) or "").strip()
        models = tuple(s.strip() for s in re.findall(r'"([^"]+)"', m.group(3)) if s.strip())
        if brand and models:
            out[brand] = models
    return out


@lru_cache(maxsize=1)
def fe_brand_slug_to_label() -> dict[str, str]:
    labels: dict[str, str] = {}
    for brand in load_fe_brand_models():
        slug = resolve_olx_brand_slug(brand)
        labels.setdefault(slug, brand)
    return labels


@lru_cache(maxsize=1)
def unique_model_token_owner() -> dict[str, str]:
    """norm token → brand_slug, якщо токен зустрічається лише в однієї марки."""
    owners: dict[str, set[str]] = {}
    for brand, models in load_fe_brand_models().items():
        slug = resolve_olx_brand_slug(brand)
        for model in models:
            for token in _identity_tokens(model):
                key = norm_text(token)
                if not key:
                    continue
                owners.setdefault(key, set()).add(slug)

    out: dict[str, str] = {}
    for key, slugs in owners.items():
        if len(slugs) != 1:
            continue
        if not _token_distinctive_enough(key):
            continue
        out[key] = next(iter(slugs))
    return out


def _token_distinctive_enough(key: str) -> bool:
    if len(key) >= 5:
        return True
    # Zeekr 001 / Porsche 911 / Fiat 500 — трицифрові коди моделей
    if re.fullmatch(r"\d{3}", key):
        return True
    if len(key) >= 4 and re.search(r"[a-zа-яёіїє]", key) and re.search(r"\d", key):
        return True
    if re.fullmatch(r"[a-z]{1,2}\d{1,2}|[a-z]{3}\d|[a-z]\d{2,3}", key):
        return True
    return False


def _identity_tokens(model: str) -> tuple[str, ...]:
    """Токени моделі для перевірки унікальності / shorthand."""
    model = (model or "").strip()
    if not model:
        return ()
    tokens: list[str] = [model]
    lower = model.lower()
    tokens.append(lower)
    compact = re.sub(r"[\s\-._]+", "", lower)
    if compact:
        tokens.append(compact)
    spaced = lower.replace("-", " ").replace(".", " ")
    if spaced != lower:
        tokens.append(spaced)
    words = [w for w in re.split(r"[\s\-./]+", model) if w]
    if len(words) >= 2:
        tokens.append(words[-1])
        tokens.append(" ".join(words[-2:]))
        if len(words) >= 3:
            tokens.append(words[0])
    return tuple(dict.fromkeys(tokens))
