from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from sift.db.models import Feed
from sift.tasks.scheduler import _is_feed_due


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

