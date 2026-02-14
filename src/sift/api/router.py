from fastapi import APIRouter

from sift.api.routes.feeds import router as feeds_router
from sift.api.routes.health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(feeds_router, prefix="/feeds", tags=["feeds"])

