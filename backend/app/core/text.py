from __future__ import annotations

import re

# Latin / UA / RU «class» у назвах Mercedes та інших
_CLASS_WORD_RE = re.compile(
    r"(?<![a-zа-яёіїє0-9])(?:class|klass|клас(?:с)?)(?![a-zа-яёіїє0-9])",
    re.IGNORECASE,
)
_LETTER_CLASS_RE = re.compile(
    r"^([a-z])[\s\-]*(?:class|klass|клас(?:с)?)\b",
    re.IGNORECASE,
)


def norm_text(value: str | None) -> str:
    """Lowercase, collapse whitespace — для порівняння брендів, регіонів тощо."""
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def unify_class_spelling(text: str) -> str:
    """«G-Класс» / «G-Class» / «g клас» → «g class» для порівняння latin+кирилиця."""
    if not text:
        return ""
    t = norm_text(text)
    t = re.sub(
        r"([a-z])[\s\-]*(?:class|klass|клас(?:с)?)\b",
        r"\1 class",
        t,
        flags=re.IGNORECASE,
    )
    t = _CLASS_WORD_RE.sub(" class ", t)
    return " ".join(t.split())


def letter_class_canonical(model: str) -> str | None:
    """«G-Класс AMG» / «G Class» / «G-Class» → «g-class»."""
    if not model:
        return None
    unified = unify_class_spelling(model)
    m = _LETTER_CLASS_RE.match(unified)
    if m:
        return f"{m.group(1).lower()}-class"
    mk = unified.replace(" ", "-")
    m2 = re.fullmatch(r"([a-z])-class", mk)
    if m2:
        return f"{m2.group(1)}-class"
    return None


def letter_class_display(model: str) -> str | None:
    """Канонічна latin-форма для FE/API: «g-class» → «G-Class»."""
    key = letter_class_canonical(model)
    if not key:
        return None
    return f"{key[0].upper()}-Class"


def letter_class_search_tokens(letter: str) -> tuple[str, ...]:
    """Усі написання X-Class для SQL/Telethon (latin + кирилиця)."""
    l = (letter or "").strip().lower()
    if not l or len(l) != 1 or not l.isalpha():
        return ()
    u = l.upper()
    tokens = [
        f"{l}-класс",
        f"{u}-Класс",
        f"{l}-клас",
        f"{u}-Class",
        f"{l}-class",
        f"{l} class",
        f"{l} класс",
        f"{l} клас",
        f"{u} Class",
        f"{u} Класс",
        f"{u} Клас",
    ]
    if l == "g":
        tokens.extend(["гелик", "gelik", "G-Класс", "G-Клас", "G Класс"])
    seen: set[str] = set()
    out: list[str] = []
    for raw in tokens:
        key = norm_text(raw)
        if key and key not in seen:
            seen.add(key)
            out.append(raw)
    return tuple(out)


def bounded_substring(hay: str, needle: str) -> bool:
    """Чи є needle у hay на межі токена («c-class» ≠ всередині «glc-class»)."""
    if not hay or not needle:
        return False
    if hay == needle:
        return True
    idx = hay.find(needle)
    while idx != -1:
        before_ok = idx == 0 or not hay[idx - 1].isalnum()
        end = idx + len(needle)
        after_ok = end == len(hay) or not hay[end].isalnum()
        if before_ok and after_ok:
            return True
        idx = hay.find(needle, idx + 1)
    return False
