AUTO_RIA_BASE_URL = "https://developers.ria.com"
AUTO_RIA_SITE_URL = "https://auto.ria.com"
LANG_ID = 4  # uk

# category_id=1 — легкові
DEFAULT_CATEGORY_ID = 1

# currency enum in search API
CURRENCY_UAH = 3
CURRENCY_USD = 1

# Період подачі (top) — https://developers.ria.com auto search
# 0=весь час, 1=година, 8=3год, 9=6год, 14=12год, 11=доба, 2=сьогодні, …
AUTO_RIA_TOP_HOUR = 1
AUTO_RIA_TOP_3H = 8
AUTO_RIA_TOP_6H = 9
AUTO_RIA_TOP_12H = 14
AUTO_RIA_TOP_24H = 11
AUTO_RIA_TOP_TODAY = 2

FUEL_NAME_TO_ID: dict[str, int] = {
    "бензин": 1,
    "дизель": 2,
    "газ": 4,
    "газ-бензин": 4,
    "газ пропан+бензин": 4,
    "газ пропан-бутан+бензин": 4,
    "газ метан+бензин": 4,
    "гібрид": 5,
    "електро": 6,
}

GEARBOX_NAME_TO_ID: dict[str, int] = {
    "механіка": 1,
    "ручна": 1,
    "автомат": 2,
    "типтронік": 3,
    "робот": 4,
    "варіатор": 5,
    "редуктор": 6,
}

# Наші регіони → (state_id, city_id). city_id=0 — усе в області (city не передаємо в API).
# ID з https://developers.ria.com/auto/states (lang_id=4).
REGION_TO_STATE_CITY: dict[str, tuple[int, int]] = {
    "м. київ": (10, 10),
    "київ": (10, 10),
    "kyiv": (10, 10),
    "kiev": (10, 10),
    "київська область": (10, 0),
    "вінницька область": (1, 0),
    "житомирська область": (2, 0),
    "тернопільська область": (3, 0),
    "хмельницька область": (4, 0),
    "львівська область": (5, 0),
    "чернігівська область": (6, 0),
    "харківська область": (7, 0),
    "сумська область": (8, 0),
    "рівненська область": (9, 0),
    "дніпропетровська область": (11, 0),
    "одеська область": (12, 0),
    "донецька область": (13, 0),
    "запорізька область": (14, 0),
    "івано-франківська область": (15, 0),
    "кіровоградська область": (16, 0),
    "волинська область": (18, 0),
    "миколаївська область": (19, 0),
    "полтавська область": (20, 0),
    "закарпатська область": (22, 0),
    "херсонська область": (23, 0),
    "черкаська область": (24, 0),
    "чернівецька область": (25, 0),
    # Луганська — відсутня в /auto/states; для AUTO.RIA лишається пост-фільтр по тексту.
}

# Короткі форми без «область»: «Хмельницька» → той самий state_id.
for _label, _pair in list(REGION_TO_STATE_CITY.items()):
    if _label.endswith(" область"):
        REGION_TO_STATE_CITY.setdefault(_label[: -len(" область")], _pair)

# Зворотній мапінг state/city → канонічний підпис (повна назва області / м. Київ).
_STATE_CITY_TO_REGION: dict[tuple[int, int], str] = {}
_STATE_ID_TO_REGION: dict[int, str] = {}
for _label, (_state_id, _city_id) in REGION_TO_STATE_CITY.items():
    if _label in ("київ", "kyiv", "kiev") or (
        not _label.endswith(" область") and _label != "м. київ"
    ):
        continue
    if _city_id:
        _STATE_CITY_TO_REGION[(_state_id, _city_id)] = _label
    else:
        _STATE_ID_TO_REGION[_state_id] = _label


def region_label_from_state_city(state_id: int | None, city_id: int | None = None) -> str | None:
    """Повертає «м. Київ» / «Одеська область» за id з AUTO.RIA, або None."""
    if state_id is None:
        return None
    try:
        sid = int(state_id)
        cid = int(city_id or 0)
    except (TypeError, ValueError):
        return None
    exact = _STATE_CITY_TO_REGION.get((sid, cid))
    if exact:
        return exact
    if cid and (sid, 0) in _STATE_CITY_TO_REGION:
        return _STATE_CITY_TO_REGION[(sid, 0)]
    return _STATE_ID_TO_REGION.get(sid)
