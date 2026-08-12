from contextlib import asynccontextmanager
import asyncio
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.secrets_guard import assert_production_secrets
from app.services.health import check_database_fast, check_kv_fast, heartbeat_age_seconds

logger = logging.getLogger(__name__)


def _init_sentry() -> None:
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.05 if not settings.DEBUG else 0.0,
            environment="debug" if settings.DEBUG else "production",
            send_default_pii=False,
        )
        logger.info("Sentry initialized")
    except Exception:
        logger.exception("Sentry init failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Secrets already validated in entrypoint; keep a second check for non-Docker runs.
    try:
        assert_production_secrets(
            debug=settings.DEBUG,
            secret_key=settings.SECRET_KEY,
            internal_api_secret=settings.INTERNAL_API_SECRET,
            admin_password=settings.ADMIN_PASSWORD,
            frontend_url=settings.FRONTEND_URL,
        )
    except RuntimeError as exc:
        logger.error("%s", exc)
        print(f"FATAL: {exc}", file=sys.stderr)
        raise RuntimeError(str(exc)) from exc

    try:
        from app.core.database import engine
        from app.core.schema_ensure import ensure_runtime_schema

        await ensure_runtime_schema(engine)
    except Exception:
        logger.exception("Runtime schema ensure failed")

    try:
        from app.services.fx_rates import refresh_process_rates

        await refresh_process_rates()
    except Exception:
        logger.debug("FX rates warmup failed", exc_info=True)

    logger.info("KV REDIS_URL=%s", settings.REDIS_URL)
    yield

    try:
        from app.services.telegram_channels.lazy_photos import close_shared_photo_service

        await close_shared_photo_service()
    except Exception:
        logger.debug("Telethon shutdown failed", exc_info=True)


_init_sentry()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
    redirect_slashes=False,
    lifespan=lifespan,
)

# CORS: браузер → backend напряму (без Next rewrite як SPOF)
_origins = list(settings.ALLOWED_ORIGINS or [])
if settings.FRONTEND_URL and settings.FRONTEND_URL.rstrip("/") not in _origins:
    _origins.append(settings.FRONTEND_URL.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(
    _request: Request,
    exc: ResponseValidationError,
) -> JSONResponse:
    """Не віддаємо сирий 500 — клієнт бачить зрозумілу помилку, в логах є деталі."""
    logger.error("Response validation failed: %s", exc.errors())
    return JSONResponse(
        status_code=502,
        content={
            "detail": "Пошук тимчасово недоступний через помилку даних. Спробуйте ще раз.",
        },
    )


@app.get("/health/live")
async def health_live():
    """Liveness для Docker — процес відповідає, без перевірки DB/KV."""
    return {"status": "ok"}


@app.get("/health")
async def health():
    db_ok = await check_database_fast()
    kv_ok = await check_kv_fast()
    try:
        worker_age = await asyncio.wait_for(heartbeat_age_seconds("worker"), timeout=1.0)
    except Exception:
        worker_age = None
    try:
        telegram_age = await asyncio.wait_for(heartbeat_age_seconds("telegram_worker"), timeout=1.0)
    except Exception:
        telegram_age = None
    # Liveness: process is up. DB/KV shown as fields for ops; do not 500 here.
    status = "ok" if db_ok and kv_ok else "degraded"
    return {
        "status": status,
        "version": "1.0.0",
        "database": db_ok,
        "kv": kv_ok,
        "worker_heartbeat_age_s": worker_age,
        "telegram_worker_heartbeat_age_s": telegram_age,
    }
