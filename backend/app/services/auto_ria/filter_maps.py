"""Мапінг фільтрів Carbit → параметри AUTO.RIA search API."""

from __future__ import annotations

from app.core.text import norm_text

# bodystyle[i] — category_id=1 (легкові), див. довідник AUTO.RIA
BODY_TYPE_TO_ID: dict[str, int] = {
    "седан": 3,
    "універсал": 4,
    "хетчбек": 5,
    "купе": 6,
    "мінівен": 7,
    "микроавтобус": 8,
    "лифтбек": 9,
    "ліфтбек": 9,
    "кабріолет": 10,
    "позашляховик": 307,
    "suv": 307,
    "кросовер": 311,
    "пікап": 317,
    "родстер": 315,
    "фургон": 320,
}

# color_id — основні кольори
COLOR_NAME_TO_RIA_ID: dict[str, int] = {
    "білий": 1,
    "чорний": 2,
    "сірий": 3,
    "срібний": 4,
    "синій": 5,
    "червоний": 6,
    "зелений": 7,
    "жовтий": 8,
    "помаранчевий": 9,
    "коричневий": 10,
    "бежевий": 11,
    "фіолетовий": 12,
}

# type[i] — розширений паливо (доповнює FUEL_NAME_TO_ID у constants)
EXTENDED_FUEL_TO_ID: dict[str, int] = {
    "газ пропан": 4,
    "газ метан": 4,
    "газ-бензин": 4,
    "газ": 4,
    "гібрид": 5,
    "електро": 6,
}

# gearbox[i]
EXTENDED_GEARBOX_TO_ID: dict[str, int] = {
    "типтронік": 3,
    "редуктор": 6,
}

# damage: 1 — не був у ДТП, 2 — був (AUTO.RIA used cars)
ACCIDENT_TO_DAMAGE: dict[str, int] = {
    "none": 1,
    "had": 2,
}

# seller / company: 1 — приват, 2 — компанія (dealer)
SELLER_TO_RIA: dict[str, int] = {
    "private": 1,
    "dealer": 2,
}

# under_credit / confiskated — типові значення API
TRI_SHOW_HIDE_TO_RIA: dict[str, int] = {
    "show": 1,
    "hide": 2,
}


def body_type_ids(labels: list[str]) -> list[int]:
    out: list[int] = []
    for label in labels:
        key = norm_text(label)
        rid = BODY_TYPE_TO_ID.get(key)
        if rid and rid not in out:
            out.append(rid)
    return out[:5]


def color_ids(labels: list[str]) -> list[int]:
    out: list[int] = []
    for label in labels:
        key = norm_text(label)
        rid = COLOR_NAME_TO_RIA_ID.get(key)
        if rid and rid not in out:
            out.append(rid)
    return out[:3]
