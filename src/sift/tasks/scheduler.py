import asyncio
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sift.config import get_settings
from sift.db.models import Feed
from sift.db.session import SessionLocal
from sift.services.feed_service import feed_service
from sift.tasks.jobs import ingest_feed_job
from sift.tasks.queueing import get_ingest_queue


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
    return f"ingest:{feed_id}"


def _has_active_job(feed_id: UUID) -> bool:
    queue = get_ingest_queue()
    existing_job = queue.fetch_job(_ingest_job_id(feed_id))
    if existing_job is None:
        return False

    status = existing_job.get_status(refresh=False)
    if status in {"queued", "started", "scheduled", "deferred"}:
        return True

    existing_job.delete()
    return False


async def enqueue_due_feeds() -> int:
    settings = get_settings()
    queue = get_ingest_queue()
    now = datetime.now(UTC)
    enqueued = 0

    async with SessionLocal() as session:
        feeds = await feed_service.list_active_feeds(session, limit=settings.scheduler_batch_size)
        for feed in feeds:
            if not _is_feed_due(feed, now):
                continue

            if _has_active_job(feed.id):
                continue

            job_id = _ingest_job_id(feed.id)
            queue.enqueue(
                ingest_feed_job,
                str(feed.id),
                job_id=job_id,
                job_timeout=600,
                result_ttl=3600,
                failure_ttl=86400,
            )
            enqueued += 1

    return enqueued


def main() -> None:
    settings = get_settings()
    print(
        "[scheduler] starting with "
        f"redis={settings.redis_url} queue={settings.ingest_queue_name} "
        f"interval={settings.scheduler_poll_interval_seconds}s"
    )

    while True:
        enqueued = asyncio.run(enqueue_due_feeds())
        if enqueued:
            print(f"[scheduler] enqueued {enqueued} feed job(s)")
        time.sleep(settings.scheduler_poll_interval_seconds)


if __name__ == "__main__":
    main()

