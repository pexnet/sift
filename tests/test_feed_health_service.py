from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, ArticleState, Feed, User
from sift.domain.schemas import FeedLifecycleUpdate
from sift.services.feed_health_service import feed_health_service
from sift.services.feed_service import FeedLifecycleError, feed_service


@pytest.mark.asyncio
async def test_transition_lifecycle_archive_marks_unread_and_is_idempotent() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="feed-lifecycle@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Security Feed", url="https://feed-health.example.com/security.xml")
        session.add(feed)
        await session.flush()

        unread_article = Article(feed_id=feed.id, source_id="u1", title="Unread", content_text="body")
        read_article = Article(feed_id=feed.id, source_id="r1", title="Read", content_text="body")
        session.add_all([unread_article, read_article])
        await session.flush()

        session.add(
            ArticleState(
                user_id=str(user.id),
                article_id=read_article.id,
                is_read=True,
                is_starred=False,
                is_archived=False,
            )
        )
        await session.commit()

        updated_feed, marked_read_count = await feed_service.transition_lifecycle(
            session=session,
            feed=feed,
            user_id=user.id,
            payload=FeedLifecycleUpdate(action="archive"),
        )
        assert updated_feed.is_archived is True
        assert updated_feed.is_active is False
        assert updated_feed.archived_at is not None
        assert marked_read_count == 1

        states_result = await session.execute(
            select(ArticleState).where(
                ArticleState.user_id == str(user.id),
                ArticleState.article_id.in_([unread_article.id, read_article.id]),
            )
        )
        states = {state.article_id: state for state in states_result.scalars().all()}
        assert states[unread_article.id].is_read is True
        assert states[read_article.id].is_read is True

        _, second_marked_count = await feed_service.transition_lifecycle(
            session=session,
            feed=updated_feed,
            user_id=user.id,
            payload=FeedLifecycleUpdate(action="archive"),
        )
        assert second_marked_count == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_transition_lifecycle_rejects_resume_for_archived_feed() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="feed-resume-error@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(
            owner_id=user.id,
            title="Archived Feed",
            url="https://feed-health.example.com/archived.xml",
            is_active=False,
            is_archived=True,
        )
        session.add(feed)
        await session.commit()

        with pytest.raises(FeedLifecycleError, match="Cannot resume an archived feed"):
            await feed_service.transition_lifecycle(
                session=session,
                feed=feed,
                user_id=user.id,
                payload=FeedLifecycleUpdate(action="resume"),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_feed_health_list_returns_expected_metrics_and_filters() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="feed-health-metrics@example.com")
        session.add(user)
        await session.flush()

        now = datetime.now(UTC)
        stale_active_feed = Feed(
            owner_id=user.id,
            title="Stale Active Feed",
            url="https://feed-health.example.com/stale.xml",
            is_active=True,
            is_archived=False,
            fetch_interval_minutes=60,
            last_fetch_success_at=now - timedelta(hours=10),
        )
        fresh_active_feed = Feed(
            owner_id=user.id,
            title="Fresh Active Feed",
            url="https://feed-health.example.com/fresh.xml",
            is_active=True,
            is_archived=False,
            fetch_interval_minutes=30,
            last_fetch_success_at=now - timedelta(hours=1),
        )
        paused_feed = Feed(
            owner_id=user.id,
            title="Paused Feed",
            url="https://feed-health.example.com/paused.xml",
            is_active=False,
            is_archived=False,
        )
        archived_feed = Feed(
            owner_id=user.id,
            title="Archived Feed",
            url="https://feed-health.example.com/archived.xml",
            is_active=False,
            is_archived=True,
            last_fetch_error="fetch failed",
            last_fetch_error_at=now - timedelta(hours=2),
        )
        session.add_all([stale_active_feed, fresh_active_feed, paused_feed, archived_feed])
        await session.flush()

        session.add_all(
            [
                Article(
                    feed_id=stale_active_feed.id,
                    source_id="s1",
                    title="Stale 1",
                    content_text="body",
                    published_at=now - timedelta(days=1),
                ),
                Article(
                    feed_id=stale_active_feed.id,
                    source_id="s2",
                    title="Stale 2",
                    content_text="body",
                    created_at=now - timedelta(days=2),
                ),
                Article(
                    feed_id=stale_active_feed.id,
                    source_id="s-old",
                    title="Old",
                    content_text="body",
                    published_at=now - timedelta(days=10),
                ),
                Article(
                    feed_id=paused_feed.id,
                    source_id="p1",
                    title="Paused read",
                    content_text="body",
                    published_at=now - timedelta(days=1),
                ),
            ]
        )
        await session.flush()

        paused_article_result = await session.execute(
            select(Article).where(Article.feed_id == paused_feed.id, Article.source_id == "p1")
        )
        paused_article = paused_article_result.scalar_one()
        session.add(
            ArticleState(
                user_id=str(user.id),
                article_id=paused_article.id,
                is_read=True,
                is_starred=False,
                is_archived=False,
            )
        )
        await session.commit()

        response = await feed_health_service.list_feed_health(
            session=session,
            user_id=user.id,
            lifecycle="all",
            q=None,
            stale_only=False,
            error_only=False,
            limit=50,
            offset=0,
        )
        assert response.summary.total_feed_count == 4
        assert response.summary.active_feed_count == 2
        assert response.summary.paused_feed_count == 1
        assert response.summary.archived_feed_count == 1
        assert response.summary.stale_feed_count == 1
        assert response.summary.error_feed_count == 1

        stale_item = next(item for item in response.items if item.feed_id == stale_active_feed.id)
        assert stale_item.is_stale is True
        assert stale_item.articles_last_7d == 2
        assert stale_item.estimated_articles_per_day_7d == 0.29
        assert stale_item.unread_count == 3

        stale_only_response = await feed_health_service.list_feed_health(
            session=session,
            user_id=user.id,
            lifecycle="active",
            q=None,
            stale_only=True,
            error_only=False,
            limit=50,
            offset=0,
        )
        assert stale_only_response.total == 1
        assert stale_only_response.items[0].feed_id == stale_active_feed.id

        error_only_response = await feed_health_service.list_feed_health(
            session=session,
            user_id=user.id,
            lifecycle="all",
            q="archived",
            stale_only=False,
            error_only=True,
            limit=50,
            offset=0,
        )
        assert error_only_response.total == 1
        assert error_only_response.items[0].feed_id == archived_feed.id

    await engine.dispose()
