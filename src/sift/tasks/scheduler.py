import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import UUID

from sift.config import get_settings
from sift.db.models import Feed
from sift.db.session import SessionLocal
from sift.observability.logging import configure_logging
from sift.observability.metrics import get_observability_metrics
from sift.observability.metrics_server import start_metrics_http_server
from sift.services.feed_service import feed_service
from sift.tasks.jobs import ingest_feed_job
from sift.tasks.queueing import get_ingest_queue

if TYPE_CHECKING:
    from rq import Queue

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SchedulerEnqueueStats:
    due_feeds: int = 0
    enqueued_jobs: int = 0


def _normalize_last_fetched_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_feed_due(feed: Feed, now: datetime) -> bool:
    if not feed.is_active:
        return False
    if feed.fetch_interval_minutes <= 0:
        return True

    last_fetched_at = _normalize_last_fetched_at(feed.last_fetched_at)
    if last_fetched_at is None:
        return True

    due_at = last_fetched_at + timedelta(minutes=feed.fetch_interval_minutes)
    return due_at <= now


def _ingest_job_id(feed_id: UUID) -> str:
    return f"ingest-{feed_id}"


def _candidate_job_ids(feed_id: UUID) -> tuple[str, ...]:
    # Keep legacy support for older job ids so scheduler dedupe still works during upgrades.
    return (_ingest_job_id(feed_id), f"ingest:{feed_id}")


def _has_active_job(feed_id: UUID, queue: "Queue | None" = None) -> bool:
    active_queue = queue or get_ingest_queue()
    for job_id in _candidate_job_ids(feed_id):
        existing_job = active_queue.fetch_job(job_id)
        if existing_job is None:
            continue

        status = existing_job.get_status(refresh=False)
        if status in {"queued", "started", "scheduled", "deferred"}:
            return True

        existing_job.delete()
    return False


def _queue_depth(queue: "Queue") -> int:
    count = getattr(queue, "count", None)
    if callable(count):
        value = count()
    else:
        value = count
    if isinstance(value, int):
        return max(0, value)
    return 0


def _queue_job_ids(queue: "Queue") -> list[str]:
    job_ids = getattr(queue, "job_ids", None)
    if callable(job_ids):
        value = job_ids()
    else:
        value = job_ids
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _queue_oldest_age_seconds(queue: "Queue", now: datetime) -> float:
    oldest_age_seconds = 0.0
    for job_id in _queue_job_ids(queue):
        job = queue.fetch_job(job_id)
        if job is None:
            continue
        enqueued_at = getattr(job, "enqueued_at", None)
        if not isinstance(enqueued_at, datetime):
            continue
        normalized = _normalize_last_fetched_at(enqueued_at)
        if normalized is None:
            continue
        age_seconds = max(0.0, (now - normalized).total_seconds())
        if oldest_age_seconds == 0.0 or age_seconds > oldest_age_seconds:
            oldest_age_seconds = age_seconds
    return oldest_age_seconds


def _refresh_queue_metrics(queue: "Queue", *, queue_name: str) -> None:
    metrics = get_observability_metrics()
    now = datetime.now(UTC)
    metrics.set_queue_depth(queue=queue_name, depth=_queue_depth(queue))
    metrics.set_queue_oldest_job_age(
        queue=queue_name,
        age_seconds=_queue_oldest_age_seconds(queue, now),
    )


async def enqueue_due_feeds() -> SchedulerEnqueueStats:
    settings = get_settings()
    metrics = get_observability_metrics()
    queue = get_ingest_queue()
    now = datetime.now(UTC)
    stats = SchedulerEnqueueStats()

    async with SessionLocal() as session:
        feeds = await feed_service.list_active_feeds(session, limit=settings.scheduler_batch_size)
        for feed in feeds:
            if not _is_feed_due(feed, now):
                metrics.record_scheduler_enqueue(result="skip_due")
                logger.debug(
                    "scheduler.enqueue.skip_due",
                    extra={
                        "event": "scheduler.enqueue.skip_due",
                        "feed_id": str(feed.id),
                        "queue_name": settings.ingest_queue_name,
                    },
                )
                continue

            stats.due_feeds += 1
            if _has_active_job(feed.id, queue):
                metrics.record_scheduler_enqueue(result="skip_active_job")
                logger.info(
                    "scheduler.enqueue.skip_active_job",
                    extra={
                        "event": "scheduler.enqueue.skip_active_job",
                        "feed_id": str(feed.id),
                        "queue_name": settings.ingest_queue_name,
                    },
                )
                continue

            job_id = _ingest_job_id(feed.id)
            try:
                queue.enqueue(
                    ingest_feed_job,
                    str(feed.id),
                    job_id=job_id,
                    job_timeout=600,
                    result_ttl=3600,
                    failure_ttl=86400,
                )
                stats.enqueued_jobs += 1
                metrics.record_scheduler_enqueue(result="success")
                logger.info(
                    "scheduler.enqueue.success",
                    extra={
                        "event": "scheduler.enqueue.success",
                        "feed_id": str(feed.id),
                        "job_id": job_id,
                        "queue_name": settings.ingest_queue_name,
                    },
                )
            except Exception as exc:
                metrics.record_scheduler_enqueue(result="error")
                logger.error(
                    "scheduler.enqueue.error",
                    extra={
                        "event": "scheduler.enqueue.error",
                        "feed_id": str(feed.id),
                        "job_id": job_id,
                        "queue_name": settings.ingest_queue_name,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )

    metrics.record_scheduler_due_feeds(count=stats.due_feeds)
    metrics.record_scheduler_enqueued_jobs(count=stats.enqueued_jobs)
    _refresh_queue_metrics(queue, queue_name=settings.ingest_queue_name)
    return stats


async def run_scheduler_loop() -> None:
    settings = get_settings()
    metrics = get_observability_metrics()
    logger.info(
        "scheduler.process.start",
        extra={
            "event": "scheduler.process.start",
            "redis_url": settings.redis_url,
            "queue_name": settings.ingest_queue_name,
            "interval_seconds": settings.scheduler_poll_interval_seconds,
        },
    )

    while True:
        loop_started = perf_counter()
        loop_result = "success"
        stats = SchedulerEnqueueStats()
        logger.info(
            "scheduler.loop.start",
            extra={"event": "scheduler.loop.start", "queue_name": settings.ingest_queue_name},
        )
        try:
            stats = await enqueue_due_feeds()
        except Exception as exc:
            loop_result = "error"
            logger.error(
                "scheduler.loop.error",
                extra={
                    "event": "scheduler.loop.error",
                    "queue_name": settings.ingest_queue_name,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
        duration_seconds = perf_counter() - loop_started
        metrics.record_scheduler_loop(result=loop_result, duration_seconds=duration_seconds)
        logger.info(
            "scheduler.loop.complete",
            extra={
                "event": "scheduler.loop.complete",
                "queue_name": settings.ingest_queue_name,
                "result": loop_result,
                "duration_ms": int(duration_seconds * 1000),
                "due_feeds": stats.due_feeds,
                "enqueued_jobs": stats.enqueued_jobs,
            },
        )
        await asyncio.sleep(settings.scheduler_poll_interval_seconds)


def main() -> None:
    settings = get_settings()
    configure_logging(
        service="sift-scheduler",
        env=settings.env,
        level=settings.log_level,
        log_format=settings.log_format,
        redact_fields=settings.log_redact_fields,
    )
    metrics_server = start_metrics_http_server(
        service_name="sift-scheduler",
        enabled=settings.observability_enabled and settings.metrics_enabled,
        host=settings.metrics_bind_host,
        port=settings.metrics_scheduler_port,
        path=settings.metrics_path,
    )
    logger.info(
        "scheduler.process.metrics",
        extra={
            "event": "scheduler.process.metrics",
            "metrics_host": metrics_server.host if metrics_server else None,
            "metrics_port": metrics_server.port if metrics_server else None,
            "metrics_path": metrics_server.path if metrics_server else None,
        },
    )
    asyncio.run(run_scheduler_loop())


if __name__ == "__main__":
    main()
