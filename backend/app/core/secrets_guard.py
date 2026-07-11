"""Reject known-weak secrets outside local/DEBUG so production cannot boot insecurely."""

from __future__ import annotations

WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "changeme",
        "secret",
        "secret_key",
    }
)

WEAK_INTERNAL_SECRETS = frozenset(
    {
        "",
        "change-me-internal",
        "changeme",
        "internal",
    }
)

WEAK_ADMIN_PASSWORDS = frozenset(
    {
        "",
        "admin",
        "admin123",
        "password",
        "123456",
    }
)


def _is_local_frontend(frontend_url: str) -> bool:
    host = (frontend_url or "").strip().lower()
    return (
        "localhost" in host
        or "127.0.0.1" in host
        or host.startswith("http://0.0.0.0")
    )


def assert_production_secrets(
    *,
    debug: bool,
    secret_key: str,
    internal_api_secret: str,
    admin_password: str,
    frontend_url: str = "",
) -> None:
    if debug or _is_local_frontend(frontend_url):
        return

    problems: list[str] = []
    if secret_key.strip().lower() in WEAK_SECRET_KEYS or len(secret_key.strip()) < 24:
        problems.append("SECRET_KEY must be a strong unique value (min 24 chars)")
    if internal_api_secret.strip().lower() in WEAK_INTERNAL_SECRETS or len(internal_api_secret.strip()) < 16:
        problems.append("INTERNAL_API_SECRET must be a strong unique value (min 16 chars)")
    if admin_password.strip().lower() in WEAK_ADMIN_PASSWORDS or len(admin_password.strip()) < 10:
        problems.append("ADMIN_PASSWORD must be strong (min 10 chars, not a default)")

    if problems:
        raise RuntimeError(
            "Refusing to start with insecure secrets. Set strong values in .env "
            "or use DEBUG=true for local development only. "
            + "; ".join(problems)
        )
