from __future__ import annotations

WEB_PARSER_SOURCES: tuple[str, ...] = (
    "auto_ria",
    "olx",
    "imperiya",
    "udrive",
    "car_market",
    "lubeavto",
    "reono",
)

PARSER_LABELS: dict[str, str] = {
    "auto_ria": "AUTO.RIA",
    "olx": "OLX",
    "imperiya": "Імперія Авто",
    "udrive": "uDrive",
    "car_market": "Car Market",
    "lubeavto": "Любе Авто",
    "reono": "REONO",
    "telegram": "Telegram",
}

# Відображені імена з multi_source / runner → canonical key
SOURCE_ALIASES: dict[str, str] = {
    "auto_ria": "auto_ria",
    "auto.ria": "auto_ria",
    "autoria": "auto_ria",
    "olx": "olx",
    "imperiya": "imperiya",
    "imperiya avto": "imperiya",
    "udrive": "udrive",
    "car_market": "car_market",
    "car market": "car_market",
    "lubeavto": "lubeavto",
    "lube avto": "lubeavto",
    "любе авто": "lubeavto",
    "reono": "reono",
    "telegram": "telegram",
    "tg": "telegram",
}

INFRA_COMPONENTS: tuple[str, ...] = (
    "backend",
    "frontend",
    "bot",
    "worker",
    "telegram_worker",
)

# Загальний статус DOWN лише якщо падає інфраструктура, не окремий парсер.
CRITICAL_COMPONENT_IDS: frozenset[str] = frozenset(
    {
        "backend",
        "frontend",
        "bot",
        "worker",
        "telegram_parser",
    }
)
