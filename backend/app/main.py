from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


def _route_paths() -> set[str]:
    return {getattr(route, "path", "") for route in app.routes if hasattr(route, "path")}


@app.get("/health")
async def health():
    paths = _route_paths()
    return {
        "status": "ok",
        "version": "1.0.0",
        "auto_ria_search_route": "/api/v1/auto-ria/search" in paths,
        "auto_ria_api_key": bool(settings.AUTO_RIA_API_KEY.strip()),
    }
