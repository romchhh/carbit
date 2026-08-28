"""Ліміти пакетів AUTO.RIA (developers.ria.com/payment) для локального обліку."""

from __future__ import annotations

# (місячний ліміт, годинний ліміт) — офіційні тарифи RIA API Platform
AUTO_RIA_QUOTA_PACKAGES: dict[str, tuple[int, int]] = {
    "free": (1_000, 30),
    "20k": (20_000, 2_000),
    "100k": (100_000, 5_000),
    "500k": (500_000, 10_000),
    "1m": (1_000_000, 20_000),
    "max": (1_000_000, 20_000),
}

AUTO_RIA_QUOTA_PACKAGE_LABELS: dict[str, str] = {
    "free": "Безкоштовний (1 000 / міс)",
    "20k": "20 000 / міс",
    "100k": "100 000 / міс",
    "500k": "500 000 / міс",
    "1m": "1 000 000 / міс (макс.)",
    "max": "1 000 000 / міс (макс.)",
}


def resolve_auto_ria_quota_limits(
    package: str,
    monthly_override: int,
    hourly_override: int,
) -> tuple[int, int, str | None]:
    """
    Повертає (monthly_limit, hourly_limit, package_key).

    AUTO_RIA_QUOTA_PACKAGE має пріоритет над MONTHLY/HOURLY.
    Якщо пакет не заданий — використовуються явні ліміти; якщо й вони 0 — free.
    """
    pkg = (package or "").strip().lower()
    if pkg in AUTO_RIA_QUOTA_PACKAGES:
        monthly, hourly = AUTO_RIA_QUOTA_PACKAGES[pkg]
        return monthly, hourly, pkg

    monthly = max(0, int(monthly_override or 0))
    hourly = max(0, int(hourly_override or 0))
    if monthly > 0 or hourly > 0:
        return monthly, hourly, None

    monthly, hourly = AUTO_RIA_QUOTA_PACKAGES["free"]
    return monthly, hourly, "free"
