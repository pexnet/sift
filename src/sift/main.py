from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sift.api.router import api_router
from sift.config import get_settings
from sift.db.session import init_models
from sift.plugins.manager import PluginManager
from sift.web.routes import router as web_router

settings = get_settings()
plugin_manager = PluginManager()
plugin_manager.load_from_paths(settings.plugin_paths)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        await init_models()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/sift/web/static"), name="static")
app.include_router(api_router)
app.include_router(web_router)


def run_dev() -> None:
    uvicorn.run("sift.main:app", host=settings.host, port=settings.port, reload=True)

