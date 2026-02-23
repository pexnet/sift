import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from sift.api.router import api_router
from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.session import SessionLocal, init_models
from sift.observability.logging import bind_request_id, configure_logging, reset_request_id
from sift.observability.metrics import get_observability_metrics
from sift.services.dev_seed_service import dev_seed_service

settings = get_settings()
configure_logging(
    service="sift-api",
    env=settings.env,
    level=settings.log_level,
    log_format=settings.log_format,
    redact_fields=settings.log_redact_fields,
)
plugin_manager = get_plugin_manager()
logger = logging.getLogger(__name__)


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


def _metrics_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path:
        return "/metrics"
    if path.startswith("/"):
        return path
    return f"/{path}"


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path


@app.middleware("http")
async def observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not settings.observability_enabled:
        return await call_next(request)

    request_id_header = settings.request_id_header
    request_id = request.headers.get(request_id_header) or uuid4().hex
    token = bind_request_id(request_id)
    start_time = perf_counter()
    logger.info(
        "api.request.start",
        extra={
            "event": "api.request.start",
            "request_id": request_id,
            "method": request.method,
            "route": _route_label(request),
        },
    )

    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        duration_seconds = perf_counter() - start_time
        duration_ms = int(duration_seconds * 1000)
        route = _route_label(request)
        get_observability_metrics().record_http_request(
            method=request.method,
            route=route,
            status_code=500,
            duration_seconds=duration_seconds,
        )
        logger.error(
            "api.request.error",
            extra={
                "event": "api.request.error",
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status_code": 500,
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise
    else:
        duration_seconds = perf_counter() - start_time
        duration_ms = int(duration_seconds * 1000)
        route = _route_label(request)
        get_observability_metrics().record_http_request(
            method=request.method,
            route=route,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        response.headers[request_id_header] = request_id
        logger.info(
            "api.request.complete",
            extra={
                "event": "api.request.complete",
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        reset_request_id(token)


if settings.observability_enabled and settings.metrics_enabled:
    metrics_path = _metrics_path(settings.metrics_path)

    @app.get(metrics_path, include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        observability_metrics = get_observability_metrics().render_prometheus()
        plugin_metrics = plugin_manager.render_telemetry_prometheus()
        body = observability_metrics + plugin_metrics
        return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")


def run_dev() -> None:
    uvicorn.run("sift.main:app", host=settings.host, port=settings.port, reload=True)
