"""Bot-side check that INTERNAL_API_SECRET is not a known weak default."""

from __future__ import annotations

WEAK_INTERNAL = frozenset({"", "change-me-internal", "changeme", "internal"})


def assert_bot_secrets(*, debug: bool, internal_api_secret: str) -> None:
    if debug:
        return
    secret = (internal_api_secret or "").strip()
    if secret.lower() in WEAK_INTERNAL or len(secret) < 16:
        raise RuntimeError(
            "Refusing to start bot with weak INTERNAL_API_SECRET. "
            "Set a strong value in .env (min 16 chars)."
        )
