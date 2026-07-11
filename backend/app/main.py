from contextlib import asynccontextmanager
import asyncio
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.secrets_guard import assert_production_secrets
from app.services.health import check_database_fast, check_kv_fast, heartbeat_age_seconds

logger = logging.getLogger(__name__)


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
        raise SystemExit(1) from exc
    logger.info("KV REDIS_URL=%s", settings.REDIS_URL)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


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
