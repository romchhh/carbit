"""Розпізнавання регіону з голосової диктовки (усі області, відмінки UA/RU)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Sequence

from app.core.text import norm_text
from app.services.search.region_cities import cities_for_region

CANONICAL_UA_REGIONS: tuple[str, ...] = (
    "Вся Україна",
    "м. Київ",
    "Київська область",
    "Вінницька область",
    "Волинська область",
    "Дніпропетровська область",
    "Донецька область",
    "Житомирська область",
    "Закарпатська область",
    "Запорізька область",
    "Івано-Франківська область",
    "Кіровоградська область",
    "Луганська область",
    "Львівська область",
    "Миколаївська область",
    "Одеська область",
    "Полтавська область",
    "Рівненська область",
    "Сумська область",
    "Тернопільська область",
    "Харківська область",
    "Херсонська область",
    "Хмельницька область",
    "Черкаська область",
    "Чернівецька область",
    "Чернігівська область",
)

# Додаткові назви / скорочення міст і областей у диктовці.
_EXTRA_REGION_ALIASES: dict[str, tuple[str, ...]] = {
    "м. Київ": ("київ", "киев", "kyiv", "kiev", "м київ", "м. київ", "києв", "києві", "києву", "киеве"),
    "Київська область": ("київськ", "киевск"),
    "Вінницька область": ("вінниц", "винниц"),
    "Волинська область": ("volyn", "волин"),
    "Дніпропетровська область": ("dnipro", "дніпр", "днепр", "dnepr"),
    "Донецька область": ("donetsk", "донец", "донецьк"),
    "Житомирська область": ("zhytomyr", "житомир"),
    "Закарпатська область": ("uzhhorod", "ужгород", "закарпат"),
    "Запорізька область": ("zaporizhzhia", "zaporizhia", "запоріж", "запорож"),
    "Івано-Франківська область": ("франківськ", "франковск", "ivanofrankivsk"),
    "Кіровоградська область": ("кропивницьк", "кировоград", "kropyvnytskyi"),
    "Луганська область": ("luhansk", "lugansk", "луганськ", "луганск"),
    "Львівська область": ("lviv", "львів", "львов", "lvov"),
    "Миколаївська область": ("mykolaiv", "миколаїв", "николаев"),
    "Одеська область": ("odesa", "odessa", "одес", "одесс"),
    "Полтавська область": ("poltava", "полтав"),
    "Рівненська область": ("rivne", "рівн", "ровно", "rovno"),
    "Сумська область": ("sumy", "сум", "сумы"),
    "Тернопільська область": ("ternopil", "тернопол", "тернопіль"),
    "Харківська область": ("kharkiv", "kharkov", "харків", "харьков"),
    "Херсонська область": ("kherson", "херсон"),
    "Хмельницька область": ("khmelnytskyi", "хмельниц", "хмельник"),
    "Черкаська область": ("cherkasy", "черкас", "черкасс"),
    "Чернівецька область": ("chernivtsi", "чернівц", "черновц"),
    "Чернігівська область": ("chernihiv", "chernigov", "черніг", "чernigov"),
    "Вся Україна": (
        "вся україна",
        "україна",
        "ukraine",
        "по україні",
        "по всій україні",
        "по всей украине",
    ),
}

_OBLAST_WORDS = ("област", "обл")


def _adjective_stem(adj: str) -> str:
    """«Волинська» → «волинськ», «Івано-Франківська» → «івано-франківськ»."""
    adj = norm_text(adj)
    if adj.endswith("ська"):
        return adj[:-1]
    if adj.endswith("ский"):
        return adj[:-2] + "ск"
    return adj


def _locative_adjective(adj: str) -> str:
    """«Волинська» → «волинській» (найчастіша форма в диктовці)."""
    adj = norm_text(adj)
    if adj.endswith("ська"):
        return adj[:-1] + "ій"
    if adj.endswith("ский"):
        return adj[:-2] + "ой"
    return adj


def _token_in_transcript(haystack: str, token: str) -> bool:
    if not haystack or not token:
        return False
    haystack = norm_text(haystack)
    token = norm_text(token)
    if len(token) <= 3:
        return (
            re.search(
                rf"(?<![a-z0-9а-яёіїєґ]){re.escape(token)}(?![a-z0-9а-яёіїєґ])",
                haystack,
                flags=re.IGNORECASE,
            )
            is not None
        )
    return token in haystack


@lru_cache(maxsize=64)
def region_match_tokens(canonical: str) -> tuple[str, ...]:
    key = norm_text(canonical)
    tokens: set[str] = set()

    if key == "вся україна":
        tokens.update(_EXTRA_REGION_ALIASES.get(canonical, ()))
        return tuple(sorted(tokens, key=len, reverse=True))

    if key == "м. київ":
        tokens.update(_EXTRA_REGION_ALIASES.get(canonical, ()))
        for kw in cities_for_region(canonical) or ():
            if len(kw) >= 3:
                tokens.add(norm_text(kw))
        return tuple(sorted(tokens, key=len, reverse=True))

    if not key.endswith(" область"):
        return (key,)

    adj = key[: -len(" область")].strip()
    tokens.add(key)
    tokens.add(key.replace(" область", " обл"))
    tokens.add(key.replace(" область", " області"))
    tokens.add(key.replace(" область", " областю"))
    tokens.add(f"{adj} област")
    tokens.add(f"{_locative_adjective(adj)} області")
    tokens.add(f"{_locative_adjective(adj)} областi")
    tokens.add(adj)
    stem = _adjective_stem(adj)
    if stem:
        tokens.add(stem)
    if adj.endswith("ська"):
        tokens.add(adj[:-2] + "ск")

    tokens.update(_EXTRA_REGION_ALIASES.get(canonical, ()))
    for kw in cities_for_region(canonical) or ():
        nk = norm_text(kw)
        if len(nk) >= 4:
            tokens.add(nk)

    return tuple(sorted(tokens, key=len, reverse=True))


def _score_region_match(haystack: str, region: str) -> int:
    best = 0
    has_oblast_word = any(w in haystack for w in _OBLAST_WORDS)
    for token in region_match_tokens(region):
        if not _token_in_transcript(haystack, token):
            continue
        score = len(token)
        if region.endswith("область") and has_oblast_word and token.endswith(("ськ", "ск", "област")):
            score += 4
        if region == "м. Київ" and "київськ" in haystack and has_oblast_word:
            score -= 6
        best = max(best, score)
    return best


def region_mentioned_in_text(text: str, region: str) -> bool:
    haystack = norm_text(text)
    if not haystack or not region:
        return False
    if norm_text(region) == "вся україна":
        return any(_token_in_transcript(haystack, t) for t in region_match_tokens(region))
    return _score_region_match(haystack, region) > 0


def infer_region_from_text(
    text: str,
    regions: Sequence[str] = CANONICAL_UA_REGIONS,
) -> str | None:
    haystack = norm_text(text)
    if not haystack:
        return None

    if region_mentioned_in_text(text, "Вся Україна"):
        return "Вся Україна"

    best_region: str | None = None
    best_score = 0

    for region in regions:
        if region == "Вся Україна":
            continue
        score = _score_region_match(haystack, region)
        if score > best_score:
            best_score = score
            best_region = region

    if not best_region:
        return None

    if best_region in ("м. Київ", "Київська область"):
        if "київськ" in haystack and any(w in haystack for w in _OBLAST_WORDS):
            return "Київська область"
        if _score_region_match(haystack, "м. Київ") >= _score_region_match(haystack, "Київська область"):
            return "м. Київ"
        return "Київська область"

    return best_region


def normalize_region_label(
    value: str | None,
    *,
    transcript: str | None = None,
    regions: Sequence[str] = CANONICAL_UA_REGIONS,
) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text in regions:
        return text

    haystack = norm_text(text)
    for region in regions:
        if norm_text(region) == haystack:
            return region

    for region in regions:
        if region_mentioned_in_text(text, region):
            return region

    if transcript:
        inferred = infer_region_from_text(transcript, regions)
        if inferred:
            return inferred

    return None
