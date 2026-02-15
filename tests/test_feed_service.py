from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Feed, User
from sift.services.feed_service import feed_service


@pytest.mark.asyncio
async def test_list_active_feeds_prioritizes_never_fetched_then_oldest() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="feeds-order@example.com")
        session.add(user)
        await session.commit()

        now = datetime.now(UTC)
        never_fetched = Feed(
            owner_id=user.id,
            title="Never fetched",
            url="https://feed-order.example.com/never.xml",
            last_fetched_at=None,
            is_active=True,
        )
        oldest_fetched = Feed(
            owner_id=user.id,
            title="Oldest fetched",
            url="https://feed-order.example.com/oldest.xml",
            last_fetched_at=now - timedelta(hours=2),
            is_active=True,
        )
        recent_fetched = Feed(
            owner_id=user.id,
            title="Recent fetched",
            url="https://feed-order.example.com/recent.xml",
            last_fetched_at=now - timedelta(minutes=10),
            is_active=True,
        )
        inactive_feed = Feed(
            owner_id=user.id,
            title="Inactive",
            url="https://feed-order.example.com/inactive.xml",
            last_fetched_at=now - timedelta(days=1),
            is_active=False,
        )
        ownerless_feed = Feed(
            owner_id=None,
            title="Ownerless",
            url="https://feed-order.example.com/ownerless.xml",
            last_fetched_at=now - timedelta(days=1),
            is_active=True,
        )

        session.add_all([never_fetched, oldest_fetched, recent_fetched, inactive_feed, ownerless_feed])
        await session.commit()

        feeds = await feed_service.list_active_feeds(session, limit=10)
        ordered_ids = [feed.id for feed in feeds]

        assert ordered_ids == [never_fetched.id, oldest_fetched.id, recent_fetched.id]

        limited = await feed_service.list_active_feeds(session, limit=2)
        assert [feed.id for feed in limited] == [never_fetched.id, oldest_fetched.id]

    await engine.dispose()
