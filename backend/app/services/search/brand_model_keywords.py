"""Ключові слова та аліаси марок/моделей для OLX, Telegram і пост-фільтрації.

Покриває latin, UA та RU написання з FE-каталогу (~87 марок / 1400+ моделей).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from app.core.text import norm_text
from app.services.search.fe_catalog import (
    _identity_tokens,
    unique_model_token_owner,
)
from app.services.olx.brand_slugs import (
    BRAND_TO_SLUG,
    MODEL_TO_SLUG,
    build_model_text_tokens,
    compose_olx_text_query,
    primary_model_text_token,
    resolve_olx_brand_slug,
    slugify,
)

MAX_TELEGRAM_KEYWORD_QUERIES = 8
MAX_SEARCH_KEYWORD_QUERIES = 10
TELEGRAM_SCAN_QUERY_PREFIX = "__scan__:"
# Глибина scan історії каналу при live-пошуку за маркою/моделлю.
TELEGRAM_HISTORY_SCAN_LIMIT = 2500

# RU/UA написання марок (slug → варіанти). Доповнює BRAND_TO_SLUG.
BRAND_SLUG_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "acura": ("акура", "acura"),
    "alfa-romeo": ("альфа ромео", "альфа-ромео", "alfa romeo", "alfa"),
    "aston-martin": ("астон мартин", "астон-мартин", "aston martin"),
    "audi": ("ауди", "ауді", "audi"),
    "baic": ("баик", "baic"),
    "bentley": ("бентли", "бентлі", "bentley"),
    "bmw": ("бмв", "bmw"),
    "buick": ("бьюик", "б'юік", "buick"),
    "byd": ("бид", "бйд", "byd"),
    "cadillac": ("кадиллак", "кадилак", "cadillac"),
    "changan": ("чанган", "changan"),
    "chery": ("чери", "чері", "chery"),
    "chevrolet": ("шевроле", "chevrolet", "chevy", "шевролє"),
    "chrysler": ("крайслер", "chrysler"),
    "citroen": ("ситроен", "сітроен", "citroen", "citroën"),
    "cupra": ("купра", "cupra"),
    "dacia": ("дачия", "дачія", "дача", "dacia"),
    "daewoo": ("дэу", "деу", "daewoo"),
    "daf": ("даф", "daf"),
    "dodge": ("додж", "dodge"),
    "dongfeng": ("dongfeng", "донгфенг", "дунфен"),
    "ds": ("ds", "дс"),
    "fiat": ("фиат", "фіат", "fiat"),
    "ford": ("форд", "ford"),
    "foton": ("foton", "фотон"),
    "gac": ("gac", "гац"),
    "geely": ("джили", "джилі", "geely"),
    "genesis": ("genesis", "дженезіс", "генезіс", "дженesіс"),
    "gmc": ("gmc", "джиэмси", "джімсі"),
    "great-wall": ("great wall", "грейт волл", "gwm", "грейт вол"),
    "haval": ("хавал", "haval"),
    "honda": ("хонда", "honda"),
    "hummer": ("hummer", "хаммер", "хамер"),
    "hyundai": ("хендай", "хюндай", "хёндай", "hyundai", "хундай"),
    "infiniti": ("инфинити", "інфініті", "infiniti", "інфінітi"),
    "isuzu": ("isuzu", "исузу", "ісузу"),
    "iveco": ("iveco", "ивеко", "івеко"),
    "jac": ("jac", "джак"),
    "jaecoo": ("jaecoo", "джику", "джеку"),
    "jaguar": ("ягуар", "jaguar"),
    "jeep": ("джип", "jeep"),
    "jetour": ("jetour", "джетур"),
    "kia": ("киа", "кіа", "kia"),
    "lada": ("лада", "ваз", "lada", "ваз-"),
    "lamborghini": ("ламборгини", "ламборджині", "lamborghini"),
    "lancia": ("lancia", "ланча"),
    "land-rover": ("land rover", "ленд ровер", "range rover", "рендж ровер", "лендровер", "ленд-ровер"),
    "lexus": ("лексус", "lexus"),
    "li-auto": ("li auto", "li-auto", "lixiang", "li xiang", "ли авто"),
    "lifan": ("lifan", "лифан"),
    "lincoln": ("линкольн", "лінкольн", "lincoln"),
    "lotus": ("lotus", "лотус"),
    "lucid": ("lucid", "люсид"),
    "man": ("man", "ман"),
    "maserati": ("maserati", "мазерати"),
    "mazda": ("мазда", "mazda"),
    "mclaren": ("mclaren", "макларен"),
    "mercedes-benz": ("mersedes", "mercedes", "mercedes-benz", "mercedes benz", "мерседес", "мерседес-бенц", "мерседес бенц", "мерс", "merс"),
    "mg": ("mg", "эмджи", "емджі"),
    "mini": ("mini", "міні", "мини"),
    "mitsubishi": ("митсубиси", "митсубиши", "міцубісі", "mitsubishi", "мітсубісі"),
    "nio": ("nio", "нио", "ніо"),
    "nissan": ("ніссан", "ниссан", "nissan", "нісан"),
    "omoda": ("omoda", "омода"),
    "opel": ("опель", "opel"),
    "peugeot": ("пежо", "peugeot"),
    "polestar": ("polestar", "полстар"),
    "porsche": ("порше", "porsche"),
    "ram": ("ram", "рам"),
    "ravon": ("ravon", "равон"),
    "renault": ("рено", "renault"),
    "rivian": ("rivian", "ривиан"),
    "rover": ("rover", "ровер"),
    "saab": ("saab", "сааб"),
    "scania": ("scania", "скания", "сканія"),
    "seat": ("seat", "сеат"),
    "skoda": ("skoda", "шкода", "škoda", "шкодa"),
    "skywell": ("skywell", "скайвелл"),
    "smart": ("smart", "смарт"),
    "ssangyong": ("ssangyong", "ssang yong", "санг йонг", "сангйонг", "санг-йонг"),
    "subaru": ("субару", "subaru", "субарy"),
    "suzuki": ("сузуки", "сузукі", "suzuki"),
    "tesla": ("tesla", "тесла", "tesla motors"),
    "toyota": ("toyota", "тойота", "toyta"),
    "volkswagen": ("volkswagen", "vw", "фольксваген", "вольксваген", "volks", "фольцваген"),
    "volvo": ("volvo", "вольво", "волво"),
    "xpeng": ("xpeng", "x peng", "xiao peng", "пенг"),
    "zaz": ("zaz", "заз"),
    "zeekr": ("zeekr", "зикр", "зікр", "зеекр"),
    "aito": ("aito", "айто"),
    "avatr": ("avatr", "аватр"),
    "deepal": ("deepal", "діпал", "дипал"),
    "denza": ("denza", "денза"),
    "exeed": ("exeed", "ексід", "ексид"),
    "hongqi": ("hongqi", "hong qi", "хунці", "хунци"),
    "huawei": ("huawei", "хуавей", "hua wei"),
    "leapmotor": ("leapmotor", "ліпмотор", "липмотор", "leap"),
    "ora": ("ora", "ора"),
    "seres": ("seres", "сереш"),
    "tank": ("tank", "танк"),
    "vinfast": ("vinfast", "вінфаст", "винфаст"),
    "voyah": ("voyah", "воях", "воя"),
    "wey": ("wey", "вей"),
    "xiaomi": ("xiaomi", "сяомі", "сяоми", "mi auto"),
    "yangwang": ("yangwang", "yang wang", "янван", "янванг"),
    "lynk-and-co": ("lynk and co", "lynk&co", "lynk-and-co", "лінк", "линк"),
}

# RU/UA варіанти популярних моделей (normalized model key → aliases)
MODEL_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    # ══ BMW ══════════════════════════════════════════════════════
    "1 series": ("1 series", "1 серия", "1 серія", "116", "118", "120", "125", "128", "130", "135", "бмв 1"),
    "2 series": ("2 series", "2 серия", "2 серія", "218", "220", "228", "230", "235", "240", "бмв 2"),
    "3 series": ("3 series", "3 серии", "3 серія", "3-seriya", "3seriya", "316", "318", "320", "323", "325", "328", "330", "335", "340", "е90", "e90", "f30", "g20"),
    "4 series": ("4 series", "4 серия", "4 серія", "418", "420", "425", "428", "430", "435", "440", "f32", "g22"),
    "5 series": ("5 series", "5 серии", "5 серія", "518", "520", "523", "525", "528", "530", "535", "540", "550", "е60", "e60", "f10", "g30"),
    "6 series": ("6 series", "6 серия", "6 серія", "625", "630", "635", "640", "645", "650", "f06", "f13"),
    "7 series": ("7 series", "7 серии", "7 серія", "725", "728", "730", "735", "740", "745", "750", "760", "е65", "e65", "f01", "g11"),
    "8 series": ("8 series", "8 серия", "8 серія", "840", "850", "m850"),
    "x1": ("x1", "бмв х1", "икс 1", "ix1"),
    "x2": ("x2", "бмв х2", "икс 2", "ix2"),
    "x3": ("x3", "бмв х3", "икс 3", "ix3", "f25", "g01"),
    "x4": ("x4", "бмв х4", "икс 4", "ix4", "f26", "g02"),
    "x5": ("x5", "бмв х5", "икс 5", "e53", "e70", "f15", "g05"),
    "x6": ("x6", "бмв х6", "икс 6", "e71", "f16", "g06"),
    "x7": ("x7", "бмв х7", "икс 7", "g07"),
    "m2": ("m2", "бмв м2", "g87"),
    "m3": ("m3", "бмв м3", "f80", "g80"),
    "m4": ("m4", "бмв м4", "f82", "g82"),
    "m5": ("m5", "бмв м5", "f90", "g90"),
    "m6": ("m6", "бмв м6"),
    "m8": ("m8", "бмв м8"),
    "i3": ("i3", "bmw i3", "бмв i3"),
    "i4": ("i4", "bmw i4", "бмв i4"),
    "i7": ("i7", "bmw i7", "бмв i7"),
    "i8": ("i8", "bmw i8", "бмв i8"),
    "ix": ("ix", "bmw ix", "бмв ix"),
    "ix1": ("ix1", "bmw ix1"),
    "ix3": ("ix3", "bmw ix3"),
    "z3": ("z3", "бмв z3"),
    "z4": ("z4", "бмв z4"),
    "xm": ("xm", "bmw xm"),

    # ══ MERCEDES-BENZ ═══════════════════════════════════════════
    # Spaced variants (c 300, c 220…) ставимо ПЕРШИМИ — Telethon шукає по словах,
    # тому "c 300" знайде пост "MERCEDES-BENZ C 300", а "c300" — ні.
    "c-class": ("c 300", "c 200", "c 220", "c 250", "c 180", "c 350", "c 400",
                 "c300", "c200", "c220", "c250", "c180", "c350", "c400", "c43", "c63",
                 "c200d", "c220d", "c250d",
                 "c-class", "c class", "c класс", "c-класс", "c клас",
                 "w204", "w205", "w206"),
    "e-class": ("e 200", "e 220", "e 250", "e 300", "e 350", "e 400", "e 450",
                 "e200", "e220", "e250", "e300", "e350", "e400", "e450", "e43", "e63",
                 "e-class", "e class", "e класс", "e-класс", "e клас",
                 "w210", "w211", "w212", "w213", "w214"),
    "s-class": ("s 350", "s 400", "s 450", "s 500", "s 550", "s 580",
                 "s350", "s400", "s450", "s500", "s550", "s580", "s63", "s65",
                 "s-class", "s class", "s класс", "s-класс",
                 "w220", "w221", "w222", "w223"),
    "a-class": ("a 180", "a 200", "a 220", "a 250",
                 "a180", "a200", "a220", "a250", "a35", "a45", "a160", "a150",
                 "a-class", "a class", "a класс", "a-класс",
                 "w176", "w177"),
    "b-class": ("b 180", "b 200", "b 220",
                 "b180", "b200", "b220", "b160",
                 "b-class", "b class", "b класс", "b-класс", "b клас",
                 "w245", "w246", "w247"),
    "g-class": ("g 500", "g 350", "g 63",
                 "g500", "g550", "g63", "g65", "g350", "g400",
                 "g-class", "g class", "g класс", "g-класс",
                 "gelik", "гелик", "гелендваген", "w463", "w464"),
    "m-class": ("m-class", "ml", "ml-class", "ml класс", "m-клас",
                 "ml250", "ml300", "ml350", "ml500", "ml63",
                 "w163", "w164", "w166"),
    "glc": ("glc", "glc-class", "gl c",
             "glc200", "glc220", "glc300", "glc350", "glc43", "glc63",
             "glc coupe", "x253", "c253"),
    "gle": ("gle", "gle-class",
             "gle300", "gle350", "gle400", "gle450", "gle500", "gle53", "gle63",
             "gle coupe", "v167", "c167"),
    "gla": ("gla", "gla-class",
             "gla180", "gla200", "gla220", "gla250", "gla35", "gla45",
             "x156", "h247"),
    "glb": ("glb", "glb-class",
             "glb180", "glb200", "glb250", "glb35", "x247"),
    "gls": ("gls", "gls-class",
             "gls350", "gls400", "gls450", "gls500", "gls580", "gls63",
             "x167"),
    "glk": ("glk", "glk-class",
             "glk200", "glk220", "glk250", "glk300", "glk350", "x204"),
    "gl": ("gl", "gl-class", "gl500", "gl63", "x164"),
    "cla": ("cla", "cla180", "cla200", "cla220", "cla250", "cla35", "cla45",
             "c117", "x118"),
    "cls": ("cls", "cls350", "cls400", "cls450", "cls500", "cls53", "cls63",
             "c218", "c257"),
    "cle": ("cle", "cle200", "cle220", "cle300"),
    "sl": ("sl", "sl350", "sl400", "sl450", "sl500", "sl55", "sl63",
            "r230", "r231", "r232"),
    "slk": ("slk", "slk200", "slk250", "slk300", "slk350", "slk55",
             "r171", "r172"),
    "slc": ("slc", "slc180", "slc200", "slc300"),
    "amg gt": ("amg gt", "amg gt 4", "amg gt s", "amg gt r", "gt63", "gt53"),
    "eqa": ("eqa", "eqa250", "eqa300", "h243"),
    "eqb": ("eqb", "eqb250", "eqb300", "x243"),
    "eqc": ("eqc", "eqc400", "n293"),
    "eqe": ("eqe", "eqe350", "eqe500", "eqe suv", "v295"),
    "eqs": ("eqs", "eqs450", "eqs580", "eqs suv", "v297"),
    "sprinter": ("sprinter", "спрінтер", "спринтер"),
    "vito": ("vito", "вито"),
    "v-class": ("v-class", "v class", "v клас", "v220", "v250", "v300", "viano", "віано"),
    "r-class": ("r-class", "r class", "r280", "r300", "r350", "r500", "w251"),
    "x-class": ("x-class", "x class", "x350d"),
    "190": ("190", "190e", "190d", "w201"),

    # ══ AUDI ════════════════════════════════════════════════════
    "a1": ("a1", "ауді a1", "ауди а1", "audi a1"),
    "a2": ("a2", "ауді a2", "audi a2"),
    "a3": ("a3", "ауді a3", "ауди а3", "audi a3", "a3 sportback", "8p", "8v", "8y"),
    "a4": ("a4", "ауді a4", "ауди а4", "audi a4", "a4 allroad", "b6", "b7", "b8", "b9"),
    "a5": ("a5", "ауді a5", "ауди а5", "audi a5", "a5 sportback"),
    "a6": ("a6", "ауді a6", "ауди а6", "audi a6", "a6 allroad", "c5", "c6", "c7", "c8"),
    "a7": ("a7", "ауді a7", "ауди а7", "audi a7"),
    "a8": ("a8", "ауді a8", "ауди а8", "audi a8", "d2", "d3", "d4", "d5"),
    "q2": ("q2", "ауді q2", "audi q2"),
    "q3": ("q3", "ауді q3", "ауди q3", "audi q3"),
    "q4 e-tron": ("q4 e-tron", "q4 etron", "q4", "audi q4"),
    "q5": ("q5", "ауді q5", "ауди q5", "audi q5", "sq5"),
    "q7": ("q7", "ауді q7", "ауди q7", "audi q7", "sq7"),
    "q8": ("q8", "ауді q8", "ауди q8", "audi q8", "sq8", "q8 e-tron", "q8 etron"),
    "r8": ("r8", "ауді r8", "audi r8"),
    "tt": ("tt", "ауді tt", "audi tt", "tts"),
    "e-tron": ("e-tron", "etron", "е-трон", "е трон", "audi etron", "e-tron gt", "etron gt"),
    "rs3": ("rs3", "rs 3", "ауді rs3"),
    "rs4": ("rs4", "rs 4", "ауді rs4"),
    "rs5": ("rs5", "rs 5", "ауді rs5"),
    "rs6": ("rs6", "rs 6", "ауді rs6"),
    "rs7": ("rs7", "rs 7", "ауді rs7"),

    # ══ VOLKSWAGEN ══════════════════════════════════════════════
    "golf": ("golf", "гольф", "golf gti", "golf gte", "golf r", "golf alltrack", "golf plus"),
    "polo": ("polo", "поло"),
    "passat": ("passat", "пасат", "passat b5", "passat b6", "passat b7", "passat b8", "passat cc", "passat alltrack"),
    "tiguan": ("tiguan", "тигуан", "тиguan", "тіguan", "tiguan allspace"),
    "touareg": ("touareg", "туарег", "toureg"),
    "arteon": ("arteon", "артеон"),
    "t-roc": ("t-roc", "troc", "t roc"),
    "t-cross": ("t-cross", "tcross", "t cross"),
    "taigo": ("taigo", "тайго"),
    "tayron": ("tayron", "тайрон"),
    "touran": ("touran", "туран"),
    "sharan": ("sharan", "шаран"),
    "beetle": ("beetle", "жук", "new beetle", "бітл"),
    "id.3": ("id.3", "id3", "id 3"),
    "id.4": ("id.4", "id4", "id 4"),
    "id.5": ("id.5", "id5", "id 5"),
    "id.6": ("id.6", "id6", "id 6"),
    "id.7": ("id.7", "id7", "id 7"),
    "id.buzz": ("id.buzz", "id buzz", "idbuzz"),
    "amarok": ("amarok", "амарок"),
    "caddy": ("caddy", "каді", "кадді"),
    "crafter": ("crafter", "крафтер"),
    "multivan": ("multivan", "мультиван"),
    "transporter": ("transporter", "транспортер", "t4", "t5", "t6", "t7"),
    "jetta": ("jetta", "джетта"),
    "phaeton": ("phaeton", "фаетон"),
    "scirocco": ("scirocco", "сірокко"),
    "eos": ("eos", "еос"),
    "up": ("up", "up!", "vw up"),

    # ══ TOYOTA ══════════════════════════════════════════════════
    "land cruiser": ("land cruiser", "ленд крузер", "lc", "lc100", "lc200", "lc300",
                      "landcruiser", "lc 200", "lc 300", "j200", "j300",
                      "land cruiser 200", "land cruiser 300"),
    "land cruiser prado": ("prado", "прадо", "land cruiser prado", "lc prado", "lcprado",
                            "lc120", "lc150", "j120", "j150", "fj120", "fj150",
                            "ленд крузер прадо"),
    "rav4": ("rav4", "рав4", "rav-4", "rav 4"),
    "camry": ("camry", "камрі", "камри"),
    "corolla": ("corolla", "королла", "корола", "corolla cross", "корола кросс"),
    "highlander": ("highlander", "хайландер"),
    "4runner": ("4runner", "4 runner", "4-runner"),
    "c-hr": ("c-hr", "chr", "c hr"),
    "yaris": ("yaris", "яріс", "ярис"),
    "yaris cross": ("yaris cross", "яріс кросс", "яріс крос"),
    "auris": ("auris", "ауріс"),
    "prius": ("prius", "пріус", "prius plus", "prius v"),
    "hilux": ("hilux", "хайлюкс", "hi-lux"),
    "fortuner": ("fortuner", "фортунер"),
    "supra": ("supra", "супра"),
    "gt86": ("gt86", "gt 86", "gr86", "gr 86", "86"),
    "bz4x": ("bz4x", "bz 4x"),
    "alphard": ("alphard", "альфард"),
    "sequoia": ("sequoia", "секвоя"),
    "tundra": ("tundra", "тундра"),
    "tacoma": ("tacoma", "такома"),
    "fj cruiser": ("fj cruiser", "fj-cruiser"),
    "avensis": ("avensis", "авенсіс"),
    "verso": ("verso", "версо"),
    "venza": ("venza", "венза"),
    "sienna": ("sienna", "сієнна"),
    "previa": ("previa", "превіа"),
    "kluger": ("kluger", "клюгер"),

    # ══ HYUNDAI ═════════════════════════════════════════════════
    "tucson": ("tucson", "тусон", "туксон"),
    "santa fe": ("santa fe", "санта фе", "grand santa fe", "гранд санта фе"),
    "elantra": ("elantra", "еланта", "avante"),
    "sonata": ("sonata", "соната"),
    "creta": ("creta", "крета"),
    "i30": ("i30", "i 30", "і30", "і 30"),
    "i20": ("i20", "i 20", "і20"),
    "i10": ("i10", "i 10", "і10"),
    "i40": ("i40", "i 40", "і40"),
    "kona": ("kona", "кона"),
    "ioniq": ("ioniq", "іонік"),
    "ioniq 5": ("ioniq 5", "ioniq5", "іонік 5"),
    "ioniq 6": ("ioniq 6", "ioniq6", "іонік 6"),
    "staria": ("staria", "старіа"),
    "palisade": ("palisade", "палісейд"),
    "accent": ("accent", "акцент"),
    "getz": ("getz", "гетц"),
    "ix35": ("ix35", "ix 35"),
    "grandeur": ("grandeur", "грандер"),
    "h-1": ("h-1", "h1", "starex", "старекс"),
    "venue": ("venue", "веню"),
    "bayon": ("bayon", "байон"),
    "solaris": ("solaris", "соларіс"),
    "veloster": ("veloster", "велостер"),
    "genesis coupe": ("genesis coupe", "генезіс купе"),

    # ══ KIA ═════════════════════════════════════════════════════
    "sportage": ("sportage", "спортейдж", "спортаж"),
    "sorento": ("sorento", "соренто"),
    "ceed": ("ceed", "сід", "pro ceed", "xceed"),
    "rio": ("rio", "ріо"),
    "picanto": ("picanto", "піканто"),
    "soul": ("soul", "соул"),
    "cerato": ("cerato", "серато", "forte"),
    "stinger": ("stinger", "стингер"),
    "ev6": ("ev6", "ev 6"),
    "ev9": ("ev9", "ev 9"),
    "niro": ("niro", "ніро"),
    "seltos": ("seltos", "селтос"),
    "carnival": ("carnival", "карнівал", "sedona", "седона"),
    "telluride": ("telluride", "телурід"),
    "xceed": ("xceed", "x ceed", "x-ceed"),
    "proceed": ("proceed", "про сід", "pro ceed"),
    "k5": ("k5", "optima", "оптіма"),
    "mohave": ("mohave", "борего", "borrego"),
    "stonic": ("stonic", "стонік"),
    "carens": ("carens", "каренс"),
    "cadenza": ("cadenza", "каденза"),

    # ══ SKODA ═══════════════════════════════════════════════════
    "octavia": ("octavia", "октавія", "октавия", "octavia a5", "octavia a7"),
    "superb": ("superb", "суперб"),
    "fabia": ("fabia", "фабія", "фабиа"),
    "karoq": ("karoq", "карок"),
    "kodiaq": ("kodiaq", "кодяк"),
    "enyaq": ("enyaq", "еняк", "enyaq iv"),
    "rapid": ("rapid", "рапід", "rapid spaceback"),
    "kamiq": ("kamiq", "камік"),
    "scala": ("scala", "скала"),
    "roomster": ("roomster", "румстер"),
    "yeti": ("yeti", "єті", "єти"),
    "citigo": ("citigo", "сітіго"),

    # ══ FORD ════════════════════════════════════════════════════
    "focus": ("focus", "фокус"),
    "fiesta": ("fiesta", "фієста"),
    "kuga": ("kuga", "куга"),
    "mondeo": ("mondeo", "мондео"),
    "explorer": ("explorer", "експлорер"),
    "mustang": ("mustang", "мустанг", "mustang mach-e", "mach-e", "mach e"),
    "edge": ("edge", "едж"),
    "ecosport": ("ecosport", "eco sport"),
    "puma": ("puma", "пума"),
    "ranger": ("ranger", "рейнджер"),
    "bronco": ("bronco", "бронко"),
    "f-150": ("f-150", "f150", "f 150"),
    "f-250": ("f-250", "f250"),
    "galaxy": ("galaxy", "галаксі"),
    "s-max": ("s-max", "s max", "smax"),
    "c-max": ("c-max", "c max", "cmax"),
    "transit": ("transit", "транзит", "transit connect", "transit custom"),
    "fusion": ("fusion", "фьюжн"),
    "escape": ("escape", "ескейп"),
    "expedition": ("expedition", "експедиція"),
    "maverick": ("maverick", "маверик"),
    "tourneo connect": ("tourneo connect", "tourneo"),
    "cougar": ("cougar", "кугуар"),

    # ══ OPEL ════════════════════════════════════════════════════
    "astra": ("astra", "астра", "astra g", "astra h", "astra j", "astra k"),
    "corsa": ("corsa", "корса"),
    "insignia": ("insignia", "інсигнія"),
    "mokka": ("mokka", "мокка", "mokka x"),
    "zafira": ("zafira", "зафіра", "zafira b", "zafira life"),
    "vectra": ("vectra", "вектра", "vectra b", "vectra c"),
    "crossland": ("crossland", "кросленд", "crossland x"),
    "grandland": ("grandland", "грандленд", "grandland x"),
    "antara": ("antara", "антара"),
    "frontera": ("frontera", "фронтера"),
    "omega": ("omega", "омега"),
    "kadett": ("kadett", "кадет"),
    "meriva": ("meriva", "мерива"),
    "agila": ("agila", "агіла"),
    "vivaro": ("vivaro", "вівaро"),
    "movano": ("movano", "мувано"),
    "combo": ("combo", "комбо"),
    "ampera": ("ampera", "ампера"),
    "adam": ("adam", "адам"),

    # ══ NISSAN ══════════════════════════════════════════════════
    "qashqai": ("qashqai", "кашкай", "qashkai"),
    "x-trail": ("x-trail", "xtrail", "икстрейл", "x trail"),
    "juke": ("juke", "джук"),
    "leaf": ("leaf", "ліф"),
    "note": ("note", "ноут"),
    "micra": ("micra", "мікра", "march"),
    "pathfinder": ("pathfinder", "патфайндер"),
    "patrol": ("patrol", "патрол", "patrol y60", "patrol y61"),
    "navara": ("navara", "навара", "frontier"),
    "almera": ("almera", "альмера", "almera classic"),
    "gt-r": ("gt-r", "gtr", "r35"),
    "370z": ("370z", "370 z", "370-z"),
    "350z": ("350z", "350 z"),
    "murano": ("murano", "мурано"),
    "armada": ("armada", "армада"),
    "kicks": ("kicks", "кікс"),
    "teana": ("teana", "теана"),
    "primera": ("primera", "прімера"),
    "maxima": ("maxima", "максима"),
    "ariya": ("ariya", "арія"),

    # ══ HONDA ═══════════════════════════════════════════════════
    "civic": ("civic", "сівік"),
    "accord": ("accord", "акорд"),
    "cr-v": ("cr-v", "crv", "cr v"),
    "hr-v": ("hr-v", "hrv", "hr v"),
    "zr-v": ("zr-v", "zrv", "zr v"),
    "jazz": ("jazz", "джаз", "fit", "фіт"),
    "pilot": ("pilot", "пілот"),
    "ridgeline": ("ridgeline", "ріджлайн"),
    "odyssey": ("odyssey", "одіссей"),
    "fr-v": ("fr-v", "frv"),
    "insight": ("insight", "інсайт"),
    "element": ("element", "елемент"),
    "legend": ("legend", "легенд"),
    "s2000": ("s2000", "s 2000"),
    "stream": ("stream", "стрім"),

    # ══ MAZDA ═══════════════════════════════════════════════════
    "cx-5": ("cx-5", "cx5", "cx 5"),
    "cx-30": ("cx-30", "cx30", "cx 30"),
    "cx-3": ("cx-3", "cx3", "cx 3"),
    "cx-50": ("cx-50", "cx50", "cx 50"),
    "cx-60": ("cx-60", "cx60", "cx 60"),
    "cx-7": ("cx-7", "cx7", "cx 7"),
    "cx-9": ("cx-9", "cx9", "cx 9"),
    "cx-90": ("cx-90", "cx90", "cx 90"),
    "mazda 3": ("mazda 3", "мазда 3", "323", "axela"),
    "mazda 6": ("mazda 6", "мазда 6", "atenza"),
    "mx-5": ("mx-5", "mx5", "miata", "roadster"),
    "mx-30": ("mx-30", "mx30"),
    "bt-50": ("bt-50", "bt50"),
    "premacy": ("premacy", "премасі"),
    "tribute": ("tribute", "трібьют"),

    # ══ SUBARU ══════════════════════════════════════════════════
    "forester": ("forester", "форестер"),
    "outback": ("outback", "аутбек"),
    "impreza": ("impreza", "імпреза", "wrx"),
    "legacy": ("legacy", "легасі"),
    "xv": ("xv", "кросстрек", "crosstrek"),
    "wrx": ("wrx", "wrx sti", "sti"),
    "brz": ("brz",),
    "tribeca": ("tribeca", "трібека"),
    "ascent": ("ascent", "асент"),
    "solterra": ("solterra", "солтера"),
    "baja": ("baja",),

    # ══ MITSUBISHI ══════════════════════════════════════════════
    "outlander": ("outlander", "аутлендер"),
    "pajero": ("pajero", "паджеро"),
    "pajero sport": ("pajero sport", "паджеро спорт"),
    "lancer": ("lancer", "лансер", "lancer evolution", "evo", "lancer x"),
    "l200": ("l200", "l-200", "l 200"),
    "eclipse cross": ("eclipse cross", "eclipse", "еклiпс"),
    "asx": ("asx", "rvr"),
    "galant": ("galant", "галант"),
    "carisma": ("carisma", "карісма"),
    "colt": ("colt", "колт"),
    "grandis": ("grandis", "грандіс"),
    "montero": ("montero", "монтеро"),
    "space star": ("space star", "спейс стар"),

    # ══ JEEP ════════════════════════════════════════════════════
    "grand cherokee": ("grand cherokee", "гранд чероки", "grand cherokee l"),
    "wrangler": ("wrangler", "вранглер", "рубікон", "rubicon", "sahara"),
    "cherokee": ("cherokee", "чероки"),
    "renegade": ("renegade", "ренегад"),
    "compass": ("compass", "компас"),
    "commander": ("commander", "командер"),
    "gladiator": ("gladiator", "гладіатор"),
    "patriot": ("patriot", "патріот"),
    "liberty": ("liberty", "лібертi"),

    # ══ CHEVROLET ═══════════════════════════════════════════════
    "cruze": ("cruze", "круз"),
    "captiva": ("captiva", "каптіва"),
    "orlando": ("orlando", "орландо"),
    "aveo": ("aveo", "авео"),
    "lacetti": ("lacetti", "лачетті", "nubira"),
    "malibu": ("malibu", "малібу"),
    "tahoe": ("tahoe", "тахо"),
    "equinox": ("equinox", "еквінокс"),
    "corvette": ("corvette", "корвет"),
    "camaro": ("camaro", "камаро"),
    "traverse": ("traverse", "траверс"),
    "silverado": ("silverado", "сільверадо"),
    "suburban": ("suburban", "субурбан"),
    "trailblazer": ("trailblazer", "трейлблейзер"),
    "blazer": ("blazer", "блейзер"),
    "spark": ("spark", "спарк", "matiz"),
    "cobalt": ("cobalt", "кобальт"),
    "colorado": ("colorado", "колорадо"),
    "express": ("express", "експрес"),
    "trax": ("trax", "тракс", "tracker"),
    "epica": ("epica", "епіка", "evanda"),
    "impala": ("impala", "імпала"),
    "bolt": ("bolt", "bolt euv"),
    "volt": ("volt", "волт"),

    # ══ RENAULT ═════════════════════════════════════════════════
    "duster": ("duster", "дастер"),
    "megane": ("megane", "меган", "мегане"),
    "clio": ("clio", "кліо"),
    "laguna": ("laguna", "лагуна"),
    "scenic": ("scenic", "сценік", "grand scenic"),
    "captur": ("captur", "каптур", "kaptur"),
    "kangoo": ("kangoo", "кангу"),
    "trafic": ("trafic", "трафік", "traffic"),
    "logan": ("logan", "логан"),
    "kadjar": ("kadjar", "каджар"),
    "koleos": ("koleos", "колеос"),
    "arkana": ("arkana", "аркана"),
    "twingo": ("twingo", "твінго"),
    "espace": ("espace", "еспас", "grand espace"),
    "master": ("master", "майстер"),
    "talisman": ("talisman", "талісман"),
    "zoe": ("zoe", "зое"),
    "austral": ("austral", "аустрал"),
    "dokker": ("dokker", "доккер"),
    "fluence": ("fluence", "флюенс"),
    "symbol": ("symbol", "симбол"),

    # ══ PEUGEOT ═════════════════════════════════════════════════
    "207": ("207", "пежо 207", "peugeot 207"),
    "208": ("208", "пежо 208", "e208"),
    "307": ("307", "пежо 307"),
    "308": ("308", "пежо 308", "e308"),
    "3008": ("3008", "пежо 3008"),
    "5008": ("5008", "пежо 5008"),
    "2008": ("2008", "пежо 2008", "e2008"),
    "407": ("407", "пежо 407"),
    "508": ("508", "пежо 508", "e508"),
    "205": ("205", "пежо 205"),
    "206": ("206", "пежо 206"),
    "107": ("107", "пежо 107"),
    "108": ("108", "пежо 108"),
    "406": ("406", "пежо 406"),
    "405": ("405", "пежо 405"),
    "301": ("301", "пежо 301"),
    "partner": ("partner", "партнер", "rifter"),
    "expert": ("expert", "експерт"),
    "boxer": ("boxer", "боксер"),
    "rcz": ("rcz",),

    # ══ CITROEN ═════════════════════════════════════════════════
    "c3": ("c3", "с3", "c3 aircross", "c3 picasso"),
    "c4": ("c4", "с4", "c4 aircross", "c4 picasso", "c4 spacetourer", "c4 cactus"),
    "c5": ("c5", "с5", "c5 aircross", "c5 x"),
    "c1": ("c1", "с1"),
    "c2": ("c2", "с2"),
    "c6": ("c6", "с6"),
    "berlingo": ("berlingo", "берлінго"),
    "xsara": ("xsara", "ксара", "xsara picasso"),
    "jumpy": ("jumpy", "джампі"),
    "jumper": ("jumper", "джампер"),
    "ds3": ("ds3", "ds 3"),
    "ds4": ("ds4", "ds 4"),
    "ds5": ("ds5", "ds 5"),
    "spacetourer": ("spacetourer", "спейс турер"),
    "dispatch": ("dispatch", "диспетч"),

    # ══ LEXUS ═══════════════════════════════════════════════════
    "rx": ("rx", "лексус rx", "rx300", "rx350", "rx400", "rx450", "rx500"),
    "nx": ("nx", "лексус nx", "nx200", "nx300", "nx350", "nx450"),
    "gx": ("gx", "лексус gx", "gx460", "gx470"),
    "lx": ("lx", "лексус lx", "lx570", "lx600"),
    "is": ("is", "лексус is", "is200", "is250", "is300", "is350"),
    "es": ("es", "лексус es", "es250", "es300", "es350"),
    "ls": ("ls", "лексус ls", "ls430", "ls460", "ls500"),
    "gs": ("gs", "лексус gs", "gs300", "gs350", "gs450"),
    "ct": ("ct", "лексус ct", "ct200h"),
    "ux": ("ux", "лексус ux", "ux200", "ux250"),
    "lc": ("lc", "лексус lc", "lc500"),
    "rc": ("rc", "лексус rc", "rc300", "rc350"),
    "rc f": ("rc f", "rcf"),
    "rz": ("rz", "лексус rz", "rz450"),

    # ══ LAND ROVER ══════════════════════════════════════════════
    "discovery": ("discovery", "дискавері", "дискавери", "диско", "disco",
                   "discovery 4", "discovery 5", "disco 4", "disco 5", "lr4", "lr3"),
    "discovery sport": ("discovery sport", "disco sport", "дискавері спорт"),
    "defender": ("defender", "дефендер", "defender 90", "defender 110", "defender 130"),
    "freelander": ("freelander", "фрілендер", "фрилендер", "freelander 2", "lr2"),
    "range rover": ("range rover", "рендж ровер", "рейндж ровер", "рр", "ренж ровер",
                     "range rover vogue"),
    "range rover sport": ("range rover sport", "рр спорт", "рендж ровер спорт", "rrs"),
    "range rover evoque": ("range rover evoque", "evoque", "евок", "євок"),
    "range rover velar": ("range rover velar", "velar", "велар"),

    # ══ ALFA ROMEO ══════════════════════════════════════════════
    "giulia": ("giulia", "джулія"),
    "stelvio": ("stelvio", "стелвіо"),
    "giulietta": ("giulietta", "джульєтта"),
    "tonale": ("tonale", "тонале"),
    "147": ("147", "альфа 147"),
    "156": ("156", "альфа 156"),
    "159": ("159", "альфа 159"),
    "166": ("166", "альфа 166"),

    # ══ SEAT ════════════════════════════════════════════════════
    "leon": ("leon", "леон"),
    "ibiza": ("ibiza", "ібіза"),
    "ateca": ("ateca", "атека"),
    "arona": ("arona", "арона"),
    "tarraco": ("tarraco", "таррако"),
    "alhambra": ("alhambra", "альгамбра"),
    "toledo": ("toledo", "толедо"),
    "altea": ("altea", "альтеа"),
    "exeo": ("exeo", "ексео"),

    # ══ CUPRA ═══════════════════════════════════════════════════
    "formentor": ("formentor", "форментор"),
    "born": ("born", "борн"),

    # ══ PORSCHE ═════════════════════════════════════════════════
    "cayenne": ("cayenne", "каен", "каенн"),
    "macan": ("macan", "макан"),
    "panamera": ("panamera", "панамера"),
    "taycan": ("taycan", "тайкан"),
    "911": ("911", "карrera", "carrera", "911 turbo", "gt3", "gt2", "turbo s"),
    "boxster": ("boxster", "боксер", "718 boxster"),
    "cayman": ("cayman", "кайман", "718 cayman"),
    "718 boxster": ("718 boxster",),
    "718 cayman": ("718 cayman", "718"),

    # ══ DACIA ═══════════════════════════════════════════════════
    "sandero": ("sandero", "сандеро", "sandero stepway"),
    "jogger": ("jogger", "джоггер"),
    "spring": ("spring", "спрінг"),

    # ══ VOLVO ═══════════════════════════════════════════════════
    "xc90": ("xc90", "xc 90"),
    "xc60": ("xc60", "xc 60"),
    "xc40": ("xc40", "xc 40"),
    "xc70": ("xc70", "xc 70"),
    "s90": ("s90", "s 90"),
    "s60": ("s60", "s 60"),
    "s40": ("s40", "s 40"),
    "s80": ("s80", "s 80"),
    "v90": ("v90", "v 90"),
    "v60": ("v60", "v 60"),
    "v50": ("v50", "v 50"),
    "v40": ("v40", "v 40"),
    "v70": ("v70", "v 70"),
    "c30": ("c30", "c 30"),
    "c40": ("c40", "c 40"),
    "c70": ("c70", "c 70"),
    "ex30": ("ex30", "ex 30"),
    "ex90": ("ex90", "ex 90"),

    # ══ TESLA ═══════════════════════════════════════════════════
    "model s": ("model s", "model-s", "models", "модел s", "модель s", "model s plaid"),
    "model 3": ("model 3", "model-3", "model3", "модел 3", "модель 3"),
    "model y": ("model y", "model-y", "modely", "модел y", "модель y", "tesla y", "тесла y"),
    "model x": ("model x", "model-x", "modelx", "модел x", "модель x", "tesla x", "тесла x"),
    "cybertruck": ("cybertruck", "кібертрак"),

    # ══ JAGUAR ══════════════════════════════════════════════════
    "f-pace": ("f-pace", "f pace", "fpace"),
    "e-pace": ("e-pace", "e pace", "epace"),
    "i-pace": ("i-pace", "i pace", "ipace"),
    "f-type": ("f-type", "f type", "ftype"),
    "xe": ("xe", "ягуар xe"),
    "xf": ("xf", "ягуар xf"),
    "xj": ("xj", "ягуар xj"),
    "xk": ("xk", "ягуар xk"),

    # ══ INFINITI ════════════════════════════════════════════════
    "qx50": ("qx50", "ex", "ex35", "ex37"),
    "qx55": ("qx55",),
    "qx60": ("qx60", "jx", "jx35"),
    "qx70": ("qx70", "fx", "fx35", "fx37", "fx45", "fx50"),
    "qx80": ("qx80", "qx56"),
    "q50": ("q50", "g37", "g35"),
    "q60": ("q60",),
    "q70": ("q70", "m37", "m56"),

    # ══ LADA / VAZ ══════════════════════════════════════════════
    "niva": ("niva", "ніва", "нива", "niva legend", "4x4"),
    "vesta": ("vesta", "веста"),
    "granta": ("granta", "гранта"),
    "kalina": ("kalina", "каліна"),
    "priora": ("priora", "пріора"),
    "largus": ("largus", "ларгус"),
    "xray": ("xray", "x ray"),
    "2101": ("2101", "копійка"),
    "2107": ("2107", "семерка"),
    "2109": ("2109", "дев'ятка"),
    "2110": ("2110", "десятка"),

    # ══ DAEWOO ══════════════════════════════════════════════════
    "lanos": ("lanos", "ланос"),
    "nexia": ("nexia", "нексія"),
    "matiz": ("matiz", "матіз"),
    "nubira": ("nubira", "нубіра"),
    "leganza": ("leganza", "леганза"),

    # ══ SSANGYONG ═══════════════════════════════════════════════
    "rexton": ("rexton", "рекстон"),
    "tivoli": ("tivoli", "тіволі"),
    "korando": ("korando", "корандо"),
    "actyon": ("actyon", "актіон"),
    "musso": ("musso", "муссо"),
    "torres": ("torres", "торрес"),
    "actyon sports": ("actyon sports", "актіон спорт"),

    # ══ CHRYSLER ════════════════════════════════════════════════
    "300c": ("300c", "300 c"),
    "grand voyager": ("grand voyager", "voyager", "гранд вояджер", "вояджер"),
    "pt cruiser": ("pt cruiser", "pt-cruiser", "пт крузер"),
    "pacifica": ("pacifica", "пасіфіка"),

    # ══ DODGE ═══════════════════════════════════════════════════
    "charger": ("charger", "чарджер"),
    "challenger": ("challenger", "челленджер"),
    "durango": ("durango", "дюранго"),
    "journey": ("journey", "джорні"),
    "caravan": ("caravan", "каравен", "grand caravan"),
    "viper": ("viper", "вайпер"),
    "avenger": ("avenger", "авенджер"),

    # ══ CADILLAC ════════════════════════════════════════════════
    "escalade": ("escalade", "ескалейд", "escalade esv"),
    "xt5": ("xt5",),
    "xt6": ("xt6",),
    "ct5": ("ct5", "cts"),
    "ct6": ("ct6",),
    "srx": ("srx",),

    # ══ GMC ═════════════════════════════════════════════════════
    "yukon": ("yukon", "юкон", "yukon xl"),
    "sierra": ("sierra", "сьєра"),
    "terrain": ("terrain", "терейн"),
    "acadia": ("acadia", "acadіа", "акадія"),
    "envoy": ("envoy", "енвой"),

    # ══ LINCOLN ═════════════════════════════════════════════════
    "navigator": ("navigator", "навігатор"),
    "aviator": ("aviator", "авіатор"),
    "nautilus": ("nautilus", "наутілус", "mkx"),
    "corsair": ("corsair", "корсар", "mkc"),
    "mkz": ("mkz", "zephyr"),

    # ══ ACURA ═══════════════════════════════════════════════════
    "mdx": ("mdx", "акура mdx"),
    "rdx": ("rdx", "акура rdx"),
    "tlx": ("tlx", "акура tlx"),

    # ══ GENESIS ═════════════════════════════════════════════════
    "g80": ("g80",),
    "g70": ("g70",),
    "gv80": ("gv80",),
    "gv70": ("gv70",),
    "gv60": ("gv60",),

    # ══ MINI ════════════════════════════════════════════════════
    "cooper": ("cooper", "купер", "cooper s"),
    "countryman": ("countryman", "кантрімен"),
    "clubman": ("clubman", "клабмен"),
    "paceman": ("paceman", "пейсмен"),

    # ══ GEELY ═══════════════════════════════════════════════════
    "coolray": ("coolray", "кулрей"),
    "atlas": ("atlas", "атлас", "atlas pro"),
    "monjaro": ("monjaro", "монджаро", "tugella"),
    "okavango": ("okavango", "окованго"),

    # ══ HAVAL ═══════════════════════════════════════════════════
    "jolion": ("jolion", "джоліон"),
    "dargo": ("dargo", "дарго"),
    "h6": ("h6", "хавал h6", "third generation h6"),
    "h9": ("h9", "хавал h9"),
    "f7": ("f7", "хавал f7"),
    "f7x": ("f7x", "хавал f7x"),

    # ══ BYD ═════════════════════════════════════════════════════
    "atto 2": ("atto 2", "atto2"),
    "atto 3": ("atto 3", "atto3"),
    "yuan plus": ("yuan plus", "yuan+", "юань плюс"),
    "yuan up": ("yuan up", "yuanup"),
    "yuan pro": ("yuan pro",),
    "han": ("han", "хань"),
    "han l": ("han l", "hanl"),
    "tang": ("tang", "тан"),
    "tang l": ("tang l", "tangl"),
    "dolphin": ("dolphin", "дельфін", "дельфин"),
    "seal": ("seal", "сіл", "сил"),
    "seal u": ("seal u", "sealu"),
    "seal 05": ("seal 05", "seal05"),
    "seal 06": ("seal 06", "seal06"),
    "seal 07": ("seal 07", "seal07"),
    "seagull": ("seagull", "сігал", "чайка"),
    "song plus": ("song plus", "song+", "сонг плюс"),
    "song l": ("song l", "songl"),
    "song pro": ("song pro",),
    "song max": ("song max",),
    "qin": ("qin", "цинь", "цинь"),
    "qin plus": ("qin plus", "qin+"),
    "qin l": ("qin l", "qinl"),
    "sea lion 05": ("sea lion 05", "sealion 05", "sealion05"),
    "sea lion 06": ("sea lion 06", "sealion 06", "sealion06"),
    "sea lion 07": ("sea lion 07", "sealion 07", "sealion07", "sealion"),
    "shark": ("shark", "шарк"),
    "shark 6": ("shark 6", "shark6"),
    "destroyer 05": ("destroyer 05", "destroyer05"),
    "frigate 07": ("frigate 07", "frigate07"),
    "xia": ("xia", "ся"),
    "leopard 5": ("leopard 5", "leopard5", "fangchengbao 5"),
    "leopard 8": ("leopard 8", "leopard8"),

    # ══ XIAOMI / AVATR / HUAWEI ═════════════════════════════════
    "su7": ("su7", "su 7", "xiaomi su7"),
    "su7 ultra": ("su7 ultra", "su7ultra"),
    "yu7": ("yu7", "yu 7", "xiaomi yu7"),
    "11": ("11", "avatr 11", "аватр 11"),
    "12": ("12", "avatr 12", "аватр 12"),
    "07": ("07", "avatr 07", "аватр 07"),
    "06": ("06", "avatr 06", "аватр 06"),
    "aito m5": ("aito m5", "m5", "айто m5"),
    "aito m7": ("aito m7", "m7", "айто m7"),
    "aito m8": ("aito m8", "m8", "айто m8"),
    "aito m9": ("aito m9", "m9", "айто m9"),
    "luxeed r7": ("luxeed r7", "r7"),

    # ══ VOYAH / LEAPMOTOR / HONGQI / DENZA ══════════════════════
    "dreamer": ("dreamer", "дрімер"),
    "free": ("free", "фрі"),
    "passion": ("passion",),
    "c10": ("c10", "leapmotor c10"),
    "c11": ("c11", "с11", "leapmotor c11"),
    "c16": ("c16", "leapmotor c16"),
    "t03": ("t03", "то3", "leapmotor t03"),
    "e-hs9": ("e-hs9", "ehs9", "hongqi e-hs9"),
    "hs5": ("hs5", "hongqi hs5"),
    "d9": ("d9", "denza d9"),
    "z9": ("z9", "denza z9"),
    "u8": ("u8", "yangwang u8"),
    "u9": ("u9", "yangwang u9"),
    "u7": ("u7", "yangwang u7"),

    # ══ CHERY ═══════════════════════════════════════════════════
    "tiggo 4": ("tiggo 4", "тигго 4", "tigo 4"),
    "tiggo 7": ("tiggo 7", "тигго 7", "tigo 7"),
    "tiggo 8": ("tiggo 8", "тигго 8", "tiggo 8 pro"),
    "tiggo 9": ("tiggo 9", "тигго 9"),
    "arrizo 7": ("arrizo 7", "арізо 7"),
    "arrizo 8": ("arrizo 8", "арізо 8"),

    # ══ ZEEKR ═══════════════════════════════════════════════════
    "001": ("001", "zeekr 001", "zeekr001", "z001", "зикр 001", "зікр 001", "зеекр 001"),
    "001 fr": ("001 fr", "zeekr 001 fr", "001fr"),
    "007": ("007", "zeekr 007", "зикр 007", "зікр 007", "зеекр 007"),
    "007 gt": ("007 gt", "zeekr 007 gt"),
    "009": ("009", "zeekr 009", "зикр 009", "зікр 009", "зеекр 009"),
    "7x": ("7x", "zeekr 7x", "зикр 7x", "зікр 7x", "зеекр 7x"),
    "8x": ("8x", "zeekr 8x"),
    "9x": ("9x", "zeekr 9x"),
    "mix": ("mix", "zeekr mix"),
    "x": ("x", "zeekr x", "зикр x", "зікр x", "зеекр x"),

    # ══ FIAT ════════════════════════════════════════════════════
    "500": ("500", "fiat 500", "500c", "500l", "500x", "чінкуеченто"),
    "bravo": ("bravo", "браво"),
    "punto": ("punto", "пунто", "grande punto"),
    "doblo": ("doblo", "добло"),
    "ducato": ("ducato", "дукато"),
    "panda": ("panda", "панда"),
    "tipo": ("tipo", "тіпо"),
    "albea": ("albea", "альбеа"),
    "stilo": ("stilo", "стіло"),
    "marea": ("marea", "мареа"),
    "sedici": ("sedici",),
    "freemont": ("freemont", "фрімонт"),

    # ══ SAAB ════════════════════════════════════════════════════
    "9-3": ("9-3", "93", "saab 9-3"),
    "9-5": ("9-5", "95", "saab 9-5"),

    # ══ SUZUKI ══════════════════════════════════════════════════
    "vitara": ("vitara", "вітара"),
    "grand vitara": ("grand vitara", "гранд вітара"),
    "swift": ("swift", "свіфт"),
    "sx4": ("sx4", "sx 4"),
    "jimny": ("jimny", "джимні"),
    "baleno": ("baleno", "балено"),

    # ══ ISUZU ═══════════════════════════════════════════════════
    "d-max": ("d-max", "dmax", "d max"),
    "trooper": ("trooper", "трупер"),
    "mu-x": ("mu-x", "mux"),

    # ══ BUICK ═══════════════════════════════════════════════════
    "enclave": ("enclave", "енклейв"),
    "encore": ("encore",),
    "envision": ("envision",),
    "lacrosse": ("lacrosse", "лакрос"),

    # ══ MASERATI ════════════════════════════════════════════════
    "ghibli": ("ghibli", "гіблі"),
    "levante": ("levante", "левaнте"),
    "quattroporte": ("quattroporte", "кватропорте"),
    "grecale": ("grecale", "грекале"),
    "granturismo": ("granturismo", "грантурізмо"),

    # ══ LAMBORGHINI ═════════════════════════════════════════════
    "urus": ("urus", "урус"),
    "huracan": ("huracan", "гурaкан", "huracán"),
    "aventador": ("aventador", "авентадор"),

    # ══ BENTLEY ═════════════════════════════════════════════════
    "bentayga": ("bentayga", "бентайга"),
    "continental gt": ("continental gt", "continental", "континенталь"),
    "flying spur": ("flying spur", "флайінг спур"),
    "mulsanne": ("mulsanne", "мулсан"),
}


@lru_cache(maxsize=512)
def collect_brand_keyword_variants(brand: str) -> tuple[str, ...]:
    """Усі написання марки для keyword-пошуку та matching."""
    brand = (brand or "").strip()
    if not brand:
        return ()

    slug = resolve_olx_brand_slug(brand)
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = norm_text(token)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(token)

    add(brand)
    add(slug)
    add(brand.replace("-", " "))
    for alias in BRAND_SLUG_EXTRA_ALIASES.get(slug, ()):
        add(alias)
    for name, name_slug in BRAND_TO_SLUG.items():
        if name_slug == slug:
            add(name)
    return tuple(out)


@lru_cache(maxsize=4096)
def collect_model_keyword_variants(brand: str, model: str) -> tuple[str, ...]:
    """Усі написання моделі для keyword-пошуку та matching."""
    model = (model or "").strip()
    if not model:
        return ()

    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = norm_text(token)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(token)

    add(model)
    add(model.replace("-", " "))

    model_key = norm_text(model)

    # ПРІОРИТЕТ: spaced-цифрові варіанти ВІДРАЗУ після назви моделі, ще до OLX-токенів.
    # Telethon шукає по словах: запит "mercedes c 300" знайде пост "MERCEDES-BENZ C 300",
    # а запит "mercedes c-class" — НЕ знайде, бо слово «class» відсутнє у пості.
    for extra in MODEL_EXTRA_ALIASES.get(model_key, ()):
        ek = norm_text(extra)
        if re.fullmatch(r"[a-z] \d{2,4}", ek):   # "c 300", "e 220", "s 500" тощо
            add(extra)

    for token in build_model_text_tokens(model, brand_slug):
        add(token)
    add(primary_model_text_token(model, brand_slug))

    for extra in MODEL_EXTRA_ALIASES.get(model_key, ()):
        add(extra)

    # Якщо model_key є значенням у MODEL_EXTRA_ALIASES (напр. «c 300» → ключ «c-class»)
    # — підвантажуємо всі алієси батьківського ключа.
    for parent_key, parent_aliases in MODEL_EXTRA_ALIASES.items():
        normed_aliases = [norm_text(a) for a in parent_aliases]
        if model_key in normed_aliases and parent_key != model_key:
            for extra in parent_aliases:
                add(extra)
            break

    target_slug = slugify(primary_model_text_token(model, brand_slug))
    for alias, alias_slug in MODEL_TO_SLUG.items():
        if alias_slug == target_slug or alias_slug == slugify(model):
            add(alias)

    out.extend(_generated_model_ru_variants(model))
    out.extend(_generated_short_model_variants(brand, model))
    deduped: list[str] = []
    seen.clear()
    for token in out:
        key = norm_text(token)
        if key and key not in seen:
            seen.add(key)
            deduped.append(token)
    return tuple(deduped)


def _generated_model_ru_variants(model: str) -> list[str]:
    """RU/UA/latin варіанти для типових патернів назв моделей (усі марки)."""
    out: list[str] = []
    base = model.strip()
    mk = norm_text(base)

    class_m = re.match(r"^([A-Za-z])-Class\b", base, re.IGNORECASE)
    if class_m:
        letter = class_m.group(1).lower()
        out.extend(
            [
                f"{letter}-class",
                f"{letter} class",
                f"{letter} класс",
                f"{letter}-класс",
                f"{letter} клас",
                f"{letter}класс",
                f"{letter}-клас",
            ]
        )

    # C 300, C 220 тощо: «letter space digits» → variant «c300», «c 300», «c-class»
    letter_digit_m = re.match(r"^([A-Za-z])\s+(\d{2,4})$", base)
    if letter_digit_m:
        letter = letter_digit_m.group(1).lower()
        digits = letter_digit_m.group(2)
        out.extend(
            [
                f"{letter}{digits}",           # c300
                f"{letter} {digits}",          # c 300
                f"{letter}-class",
                f"{letter} class",
                f"{letter} клас",
                f"{letter} класс",
            ]
        )

    series_m = re.match(r"^(\d+)\s+Series\b", base, re.IGNORECASE)
    if series_m:
        num = series_m.group(1)
        out.extend(
            [
                f"{num} series",
                f"{num} серии",
                f"{num} серія",
                f"{num}-series",
                f"{num}seriya",
            ]
        )

    if re.search(r"model\s+[sx3y]", base, re.IGNORECASE):
        for cyr in ("модел", "модель"):
            rest = re.sub(r"^model\s+", "", base, flags=re.IGNORECASE)
            out.append(f"{cyr} {rest}")

    # ID.3 / ID.4 / e-tron / C-HR / T-Roc
    id_m = re.match(r"^id\.?\s*(\d+)$", base, re.IGNORECASE)
    if id_m:
        num = id_m.group(1)
        out.extend([f"id{num}", f"id {num}", f"id.{num}"])

    if re.search(r"e-tron|e tron", base, re.IGNORECASE):
        out.append(re.sub(r"\s+", " ", base, flags=re.IGNORECASE).lower())
        out.append(re.sub(r"[\s\-]+", "", base, flags=re.IGNORECASE).lower())

    hyphen_word = re.match(r"^([A-Za-z])-([A-Za-z0-9]+)$", base)
    if hyphen_word:
        a, b = hyphen_word.group(1).lower(), hyphen_word.group(2).lower()
        out.extend([f"{a}{b}", f"{a} {b}", f"{a}-{b}"])

    words = [w for w in re.split(r"[\s\-./]+", base) if w]
    if len(words) >= 2:
        out.append(words[-1])
        out.append(" ".join(words[-2:]).lower())
        if len(words[-1]) >= 4:
            out.append(words[-1].lower())

    alnum = re.sub(r"[\s\-._]+", "", base.lower())
    if alnum and alnum != base.lower():
        out.append(alnum)

    if mk.startswith("land cruiser"):
        out.extend(["lc", "land cruiser", "lc prado", "land cruiser prado"])

    if mk.startswith("range rover"):
        out.append("rr")

    return out


# Занадто короткі / шумні токени не годяться для SQL ILIKE і standalone match
_SQL_SKIP_TOKENS = frozenset({"model", "models", "s", "x", "y", "3"})


def _model_core_tokens(brand: str, model: str) -> tuple[str, ...]:
    """Компактні токени моделі для brand+model shorthand (усі марки)."""
    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    base = model.strip()
    mk = norm_text(base)
    tokens: list[str] = []

    def add(raw: str) -> None:
        t = (raw or "").strip()
        if t and norm_text(t) not in {norm_text(x) for x in tokens}:
            tokens.append(t)

    add(base)
    add(base.lower())
    add(primary_model_text_token(model, brand_slug).replace("-", " "))
    compact = re.sub(r"[\s\-._]+", "", base.lower())
    if compact:
        add(compact)

    for token in _identity_tokens(model):
        add(token)

    tesla_m = re.match(r"^model\s+([3sxy])$", mk)
    if tesla_m:
        add(tesla_m.group(1))
        add(f"model {tesla_m.group(1)}")

    series_m = re.match(r"^(\d+)\s+series$", mk)
    if series_m:
        add(series_m.group(1))

    class_m = re.match(r"^([a-z])-class$", mk)
    if class_m:
        add(class_m.group(1))

    id_m = re.match(r"^id\.?\s*(\d+)$", mk)
    if id_m:
        add(f"id{id_m.group(1)}")
        add(f"id {id_m.group(1)}")

    letter_num = re.fullmatch(r"[a-z]{1,3}\d+[a-z0-9]*", compact)
    if letter_num:
        add(compact)

    return tuple(tokens[:16])


def _generated_short_model_variants(brand: str, model: str) -> list[str]:
    """Colloquial форми для будь-якої марки: «toyota prado», «vw golf», «ауди a4» …"""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not model:
        return []

    out: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        token = (raw or "").strip()
        if not token:
            return
        key = norm_text(token)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(token)

    brand_tokens = list(collect_brand_keyword_variants(brand)) if brand else []
    cores = _model_core_tokens(brand, model)

    for core in cores:
        if not core:
            continue
        core_key = norm_text(core)
        # Голі «3» / «s» / «x» / «y» ловлять рік, ціну, пробіг — лише з маркою.
        standalone_ok = core_key not in _SQL_SKIP_TOKENS and not (
            len(core_key) <= 1 or (core_key.isdigit() and len(core_key) <= 2)
        )
        if standalone_ok:
            add(core)
        if not brand_tokens:
            continue
        for bt in brand_tokens:
            if len(norm_text(bt)) < 2:
                continue
            add(f"{bt} {core}")
            if re.fullmatch(r"\d{3}", core_key) or re.fullmatch(r"[a-z0-9]{2,4}", core_key):
                add(f"{bt}{core}".replace(" ", ""))

    return out


def _allows_distinctive_model_without_brand(brand: str, model: str) -> bool:
    """Модель у FE унікальна для марки → brand може не бути в тексті."""
    slug = resolve_olx_brand_slug(brand) if brand else ""
    if not slug or not model:
        return False

    index = unique_model_token_owner()
    for token in _identity_tokens(model):
        if index.get(norm_text(token)) == slug:
            return True

    if slug == "tesla" and re.match(r"^model\s+[3sxy]$", norm_text(model)):
        return True
    return False


def _brand_shorthand_variants(brand: str, model: str) -> tuple[str, ...]:
    """Варіанти «brand + core» для всіх марок."""
    return tuple(
        v
        for v in _generated_short_model_variants(brand, model)
        if " " in v
        and any(
            norm_text(bt) in norm_text(v)
            for bt in collect_brand_keyword_variants(brand)
        )
    )


def _regex_model_patterns(brand: str, model: str) -> tuple[str, ...]:
    """Regex для colloquial написань — усі марки."""
    brand_slug = resolve_olx_brand_slug(brand) if brand else ""
    mk = norm_text(model)
    patterns: list[str] = []
    seen: set[str] = set()

    def add(pat: str) -> None:
        if pat and pat not in seen:
            seen.add(pat)
            patterns.append(pat)

    tesla_m = re.match(r"^model\s+([3sxy])$", mk)
    if tesla_m:
        token = re.escape(tesla_m.group(1))
        for pat in (
            rf"\bmodel[\s\-]?{token}\b",
            rf"\bмодел[\s\-]?{token}\b",
            rf"\bмодель[\s\-]?{token}\b",
            rf"\btesla[\s\-]?{token}\b",
            rf"\bтесла[\s\-]?{token}\b",
        ):
            add(pat)

    series_m = re.match(r"^(\d+)\s+series$", mk)
    if series_m:
        num = re.escape(series_m.group(1))
        add(rf"\b{num}[\s\-]?series\b")
        add(rf"\b{num}[\s\-]?ser(?:ii|iya|ies|і)\b")

    class_m = re.match(r"^([a-z])-class$", mk)
    if class_m:
        letter = re.escape(class_m.group(1))
        add(rf"\b{letter}[\s\-]?class\b")
        add(rf"\b{letter}[\s\-]?клас")

    id_m = re.match(r"^id\.?\s*(\d+)$", mk)
    if id_m:
        num = re.escape(id_m.group(1))
        add(rf"\bid[\s\-.]?{num}\b")

    for core in _model_core_tokens(brand, model):
        c = norm_text(core)
        if len(c) < 2:
            continue
        esc = re.escape(c)
        if len(c) <= 3 and c.isalpha():
            add(rf"(?<![a-zа-яёіїє0-9]){esc}(?![a-zа-яёіїє0-9])")
        elif " " in c or "-" in c:
            add(esc.replace(r"\ ", r"[\s\-]?").replace(r"\-", r"[\s\-]?"))

    if brand:
        for bt in collect_brand_keyword_variants(brand):
            b = norm_text(bt)
            if len(b) < 2:
                continue
            b_esc = re.escape(b)
            for core in _model_core_tokens(brand, model):
                c = norm_text(core)
                if len(c) < 1:
                    continue
                if c.isdigit() and len(c) == 1:
                    continue
                c_esc = re.escape(c)
                add(rf"\b{b_esc}[\s\-./]{{0,3}}{c_esc}\b")
                if len(c) <= 4 and re.fullmatch(r"[a-z0-9]+", c):
                    add(rf"\b{b_esc}[\s\-./]{{0,3}}{c_esc}(?:[\s\-./]|$|\d)")

    return tuple(patterns[:40])


def _regex_model_match(hay: str, brand: str, model: str) -> bool:
    for pattern in _regex_model_patterns(brand, model):
        if re.search(pattern, hay, re.IGNORECASE):
            return True
    return False


def build_search_keyword_queries(
    brand: str,
    model: str = "",
    *,
    max_queries: int = MAX_SEARCH_KEYWORD_QUERIES,
) -> list[str]:
    """Комбінації brand+model для Telethon / OLX / matching (latin + RU)."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return []

    olx_primary = compose_olx_text_query(brand, model) if brand else ""
    brand_tokens = list(collect_brand_keyword_variants(brand)) if brand else []
    model_tokens = list(collect_model_keyword_variants(brand, model)) if model else [""]

    seen: set[str] = set()
    out: list[str] = []

    def add(query: str) -> None:
        q = (query or "").strip()
        if not q:
            return
        key = norm_text(q)
        if key in seen:
            return
        seen.add(key)
        out.append(q)

    if olx_primary:
        add(olx_primary)
    for bt in brand_tokens:
        for mt in model_tokens:
            if bt and mt:
                add(f"{bt} {mt}")
            elif bt:
                add(bt)
            elif mt:
                add(mt)
    if model:
        for bt in brand_tokens:
            add(bt)

    # Якщо модель унікально ідентифікує бренд (Discovery → Land Rover, Touareg → VW тощо),
    # додаємо standalone model-tokens — постачальник може не вказати назву бренду в тексті.
    if brand and model:
        if _allows_distinctive_model_without_brand(brand, model):
            for mt in model_tokens:
                mt_key = norm_text(mt)
                if not mt_key or mt_key in _SQL_SKIP_TOKENS:
                    continue
                if len(mt_key) >= 4:  # мінімальна довжина щоб уникнути шуму
                    add(mt)

    return out[: max(1, max_queries)]


def filter_sql_search_tokens(variants: tuple[str, ...] | list[str], *, limit: int = 6) -> tuple[str, ...]:
    """Безпечні ключі для Telegram SQL ILIKE (без «s», «models» тощо)."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in variants:
        token = (raw or "").strip()
        if not token:
            continue
        key = norm_text(token)
        if not key or key in seen or key in _SQL_SKIP_TOKENS:
            continue
        if len(key) <= 2 and not any(ch.isdigit() for ch in key):
            continue
        seen.add(key)
        out.append(token)
        if len(out) >= limit:
            break
    return tuple(out)


def build_telegram_keyword_queries(filters) -> list[str]:
    """Deprecated: один scan-job на канал; лишено для тестів."""
    brand = (getattr(filters, "brand", None) or "").strip()
    model = (getattr(filters, "model", None) or "").strip()
    if not brand and not model:
        return []
    return [encode_telegram_scan_job(brand, model)]


def encode_telegram_scan_job(brand: str, model: str = "") -> str:
    """Payload для keyword_search_queue: повний scan історії + variant matching."""
    payload = {
        "brand": (brand or "").strip(),
        "model": (model or "").strip(),
    }
    return TELEGRAM_SCAN_QUERY_PREFIX + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )


def decode_telegram_scan_job(query: str) -> dict[str, str] | None:
    q = (query or "").strip()
    if not q.startswith(TELEGRAM_SCAN_QUERY_PREFIX):
        return None
    try:
        data = json.loads(q[len(TELEGRAM_SCAN_QUERY_PREFIX) :])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    brand = str(data.get("brand") or "").strip()
    if not brand:
        return None
    return {"brand": brand, "model": str(data.get("model") or "").strip()}


def _haystacks_for_match(text: str) -> tuple[str, ...]:
    """Raw + homoglyph-normalized (ТЕSLA → TESLA), без дублікатів."""
    raw = text or ""
    if not raw:
        return ()
    try:
        from app.services.olx.parser import _normalize_title_for_match

        alt = _normalize_title_for_match(raw)
    except ImportError:
        alt = raw
    if alt != raw:
        return (raw, alt)
    return (raw,)


def message_matches_search_filters(text: str, brand: str, model: str = "") -> bool:
    """Чи підходить текст повідомлення за brand/model (усі keyword-варіанти)."""
    brand = (brand or "").strip()
    model = (model or "").strip()
    if not brand and not model:
        return False
    for hay in _haystacks_for_match(text):
        if brand and not text_matches_brand_filter(hay, brand, model=model):
            continue
        if model and not text_matches_model_filter(hay, model, brand=brand):
            continue
        return True
    return False


def _variant_in_haystack(variant: str, hay: str) -> bool:
    v = norm_text(variant)
    if not v or not hay:
        return False
    # Шумні однолітерні/цифрові токени без контексту марки.
    if v in _SQL_SKIP_TOKENS and " " not in (variant or "").strip().lower():
        return False
    if len(v) <= 2 and v.isalpha():
        return bool(
            re.search(
                rf"(?<![a-zа-яёіїє0-9]){re.escape(v)}(?![a-zа-яёіїє0-9])",
                hay,
            )
        )
    if v.isdigit() and len(v) <= 2:
        return bool(
            re.search(
                rf"(?<![a-zа-яёіїє0-9]){re.escape(v)}(?![a-zа-яёіїє0-9])",
                hay,
            )
        )
    if v in hay:
        return True
    # «c300» ↔ «c 300»: однолітерний префікс + цифри — шукаємо обидві форми.
    m = re.fullmatch(r"([a-z])(\d{2,4})", v)
    if m:
        alt = f"{m.group(1)} {m.group(2)}"
        return alt in hay
    return False


@lru_cache(maxsize=128)
def _distinctive_model_tokens_for_brand_slug(slug: str) -> tuple[str, ...]:
    if not slug:
        return ()
    return tuple(
        sorted(
            token
            for token, owner in unique_model_token_owner().items()
            if owner == slug and len(token) >= 4
        )
    )


def _brand_distinctive_model_in_text(haystack: str, brand: str) -> bool:
    """Чи є в тексті унікальна модель цієї марки (для brand-only фільтра)."""
    slug = resolve_olx_brand_slug(brand) if brand else ""
    if not slug:
        return False
    hay = norm_text(haystack)
    if not hay:
        return False
    for token in _distinctive_model_tokens_for_brand_slug(slug):
        if _variant_in_haystack(token, hay):
            return True
    return False


def text_matches_brand_filter(haystack: str, brand: str, *, model: str = "") -> bool:
    if not haystack or not brand:
        return True
    for raw in _haystacks_for_match(haystack):
        hay = norm_text(raw)
        if not hay:
            continue
        for variant in collect_brand_keyword_variants(brand):
            if _variant_in_haystack(variant, hay):
                return True
        if model:
            for shorthand in _brand_shorthand_variants(brand, model):
                if _variant_in_haystack(shorthand, hay):
                    return True
            if _allows_distinctive_model_without_brand(brand, model) and text_matches_model_filter(
                raw, model, brand=brand
            ):
                return True
        elif _brand_distinctive_model_in_text(raw, brand):
            # Brand-only search: «Countryman 2013» без слова Mini все одно Mini.
            return True
    return False


def text_matches_model_filter(haystack: str, model: str, *, brand: str = "") -> bool:
    if not haystack or not model:
        return True
    for raw in _haystacks_for_match(haystack):
        hay = norm_text(raw)
        if not hay:
            continue
        for variant in collect_model_keyword_variants(brand, model):
            if _variant_in_haystack(variant, hay):
                return True
        if norm_text(model) in hay:
            return True
        if _regex_model_match(hay, brand, model):
            return True
        from app.services.olx.parser import _title_has_model

        if _title_has_model(hay, model, brand=brand) or _title_has_model(raw, model, brand=brand):
            return True
    return False
