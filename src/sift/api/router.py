from fastapi import APIRouter

from sift.api.routes.articles import router as articles_router
from sift.api.routes.auth import router as auth_router
from sift.api.routes.feeds import router as feeds_router
from sift.api.routes.folders import router as folders_router
from sift.api.routes.health import router as health_router
from sift.api.routes.imports import router as imports_router
from sift.api.routes.rules import router as rules_router
from sift.api.routes.streams import router as streams_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(feeds_router, prefix="/feeds", tags=["feeds"])
api_router.include_router(folders_router, prefix="/folders", tags=["folders"])
api_router.include_router(articles_router, prefix="/articles", tags=["articles"])
api_router.include_router(imports_router, prefix="/imports", tags=["imports"])
api_router.include_router(rules_router, prefix="/rules", tags=["rules"])
api_router.include_router(streams_router, prefix="/streams", tags=["streams"])

