from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.services.health import check_database, check_kv, heartbeat_age_seconds

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
    redirect_slashes=False,
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
    db_ok = await check_database()
    kv_ok = await check_kv()
    worker_age = await heartbeat_age_seconds("worker")
    telegram_age = await heartbeat_age_seconds("telegram_worker")
    status = "ok" if db_ok and kv_ok else "degraded"
    return {
        "status": status,
        "version": "1.0.0",
        "database": db_ok,
        "kv": kv_ok,
        "worker_heartbeat_age_s": worker_age,
        "telegram_worker_heartbeat_age_s": telegram_age,
    }
