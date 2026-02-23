import asyncio
import logging
from collections.abc import Mapping
from time import perf_counter
from uuid import UUID

from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.session import SessionLocal
from sift.observability.metrics import get_observability_metrics
from sift.services.ingestion_service import FeedNotFoundError, ingestion_service

logger = logging.getLogger(__name__)


async def _run_ingest(feed_id: UUID) -> dict[str, object]:
    async with SessionLocal() as session:
        result = await ingestion_service.ingest_feed(session, feed_id=feed_id, plugin_manager=get_plugin_manager())
    return result.model_dump(mode="json")


def ingest_feed_job(feed_id: str) -> dict[str, object]:
    settings = get_settings()
    started_at = perf_counter()
    logger.info(
        "worker.job.start",
        extra={
            "event": "worker.job.start",
            "feed_id": feed_id,
            "job_id": f"ingest-{feed_id}",
            "queue_name": settings.ingest_queue_name,
        },
    )

    try:
        parsed_id = UUID(feed_id)
    except ValueError as exc:
        payload: dict[str, object] = {"feed_id": feed_id, "status": "invalid", "errors": [str(exc)]}
        _record_worker_job_observability(feed_id=feed_id, payload=payload, started_at=started_at)
        return payload

    try:
        payload = dict(asyncio.run(_run_ingest(parsed_id)))
    except FeedNotFoundError as exc:
        payload = {"feed_id": feed_id, "status": "missing", "errors": [str(exc)]}
        _record_worker_job_observability(feed_id=feed_id, payload=payload, started_at=started_at)
        return payload
    except Exception as exc:  # noqa: BLE001
        duration_seconds = perf_counter() - started_at
        get_observability_metrics().record_worker_job(result="failure", duration_seconds=duration_seconds)
        logger.error(
            "worker.job.error",
            extra={
                "event": "worker.job.error",
                "feed_id": feed_id,
                "job_id": f"ingest-{feed_id}",
                "queue_name": settings.ingest_queue_name,
                "duration_ms": int(duration_seconds * 1000),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise

    payload["status"] = "ok"
    _record_worker_job_observability(feed_id=feed_id, payload=payload, started_at=started_at)
    return payload


def _record_worker_job_observability(*, feed_id: str, payload: Mapping[str, object], started_at: float) -> None:
    settings = get_settings()
    errors = payload.get("errors")
    has_errors = isinstance(errors, list) and bool(errors)
    result = "success" if payload.get("status") == "ok" and not has_errors else "failure"
    duration_seconds = perf_counter() - started_at
    get_observability_metrics().record_worker_job(result=result, duration_seconds=duration_seconds)
    logger.info(
        "worker.job.complete",
        extra={
            "event": "worker.job.complete",
            "feed_id": feed_id,
            "job_id": f"ingest-{feed_id}",
            "queue_name": settings.ingest_queue_name,
            "result": result,
            "status": payload.get("status"),
            "duration_ms": int(duration_seconds * 1000),
        },
    )
