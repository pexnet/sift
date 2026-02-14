from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sift.api.router import api_router
from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.session import SessionLocal, init_models
from sift.services.dev_seed_service import dev_seed_service
from sift.web.routes import router as web_router

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
app.mount("/static", StaticFiles(directory="src/sift/web/static"), name="static")
app.include_router(api_router)
app.include_router(web_router)


def run_dev() -> None:
    uvicorn.run("sift.main:app", host=settings.host, port=settings.port, reload=True)

