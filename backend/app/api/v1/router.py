from fastapi import APIRouter

from app.api.v1 import auth, users, searches, listings, favorites, notifications, billing, telegram, internal, admin

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(searches.router)
api_router.include_router(listings.router)
api_router.include_router(favorites.router)
api_router.include_router(notifications.router)
api_router.include_router(billing.router)
api_router.include_router(telegram.router)
api_router.include_router(internal.router)
api_router.include_router(admin.router)
