from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sift.api.router import api_router
from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.session import SessionLocal, init_models
from sift.services.dev_seed_service import dev_seed_service

settings = get_settings()
plugin_manager = get_plugin_manager()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        await init_models()
    if settings.env.lower() == "development" and settings.dev_seed_enabled:
        async with SessionLocal() as session:
            await dev_seed_service.run(session=session, settings=settings)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
app.include_router(api_router)


def run_dev() -> None:
    uvicorn.run("sift.main:app", host=settings.host, port=settings.port, reload=True)

