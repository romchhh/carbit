"""Розбиття складних марок FE (Huawei → Aito/Luxeed/Seres) для API-пошуку."""

from __future__ import annotations

from app.core.text import norm_text

_HUAWEI_SUBBRANDS = {
    "aito": "Aito",
    "luxeed": "Luxeed",
    "seres": "Seres",
}


def split_huawei_subbrand(brand: str, model: str) -> tuple[str, str]:
    """Huawei + «Aito M5» → Aito + M5 (каталог Imperiya/OLX)."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if norm_text(brand) != "huawei" or not model:
        return brand, model

    parts = model.split(None, 1)
    if len(parts) != 2:
        return brand, model

    prefix_n = norm_text(parts[0])
    subbrand = _HUAWEI_SUBBRANDS.get(prefix_n)
    if subbrand:
        return subbrand, parts[1].strip()
    return brand, model
