from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from sift.db.models import Feed
from sift.tasks.scheduler import _has_active_job, _ingest_job_id, _is_feed_due


@dataclass
class FeedStub:
    is_active: bool
    fetch_interval_minutes: int
    last_fetched_at: datetime | None


def _feed(
    *,
    is_active: bool = True,
    fetch_interval_minutes: int = 15,
    last_fetched_at: datetime | None = None,
) -> Feed:
    return cast(
        Feed,
        FeedStub(
            is_active=is_active,
            fetch_interval_minutes=fetch_interval_minutes,
            last_fetched_at=last_fetched_at,
        ),
    )


def test_is_feed_due_when_never_fetched() -> None:
    now = datetime.now(UTC)
    assert _is_feed_due(_feed(last_fetched_at=None), now) is True


def test_is_feed_due_false_when_interval_not_elapsed() -> None:
    now = datetime.now(UTC)
    feed = _feed(last_fetched_at=now - timedelta(minutes=5), fetch_interval_minutes=15)
    assert _is_feed_due(feed, now) is False


def test_is_feed_due_true_when_interval_elapsed() -> None:
    now = datetime.now(UTC)
    feed = _feed(last_fetched_at=now - timedelta(minutes=20), fetch_interval_minutes=15)
    assert _is_feed_due(feed, now) is True


def test_is_feed_due_false_when_inactive() -> None:
    now = datetime.now(UTC)
    assert _is_feed_due(_feed(is_active=False, last_fetched_at=None), now) is False


def test_ingest_job_id_uses_rq_compatible_delimiter() -> None:
    job_id = _ingest_job_id(uuid4())
    assert ":" not in job_id


@dataclass
class JobStub:
    status: str
    deleted: bool = False

    def get_status(self, *, refresh: bool) -> str:
        return self.status

    def delete(self) -> None:
        self.deleted = True


@dataclass
class QueueStub:
    jobs: dict[str, JobStub]

    def fetch_job(self, job_id: str) -> JobStub | None:
        return self.jobs.get(job_id)


def test_has_active_job_reads_legacy_job_ids_for_dedupe() -> None:
    feed_id = uuid4()
    legacy_job = JobStub(status="queued")
    queue = QueueStub(jobs={f"ingest:{feed_id}": legacy_job})

    assert _has_active_job(feed_id, queue=queue) is True


def test_has_active_job_deletes_stale_legacy_jobs() -> None:
    feed_id = uuid4()
    legacy_job = JobStub(status="finished")
    queue = QueueStub(jobs={f"ingest:{feed_id}": legacy_job})

    assert _has_active_job(feed_id, queue=queue) is False
    assert legacy_job.deleted is True
