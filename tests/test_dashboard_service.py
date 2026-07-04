from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import (
    Article,
    ArticleState,
    Feed,
    FeedRecommendation,
    KeywordStream,
    KeywordStreamMatch,
    User,
    UserPrioritizationProfile,
)
from sift.domain.schemas import DashboardPriorityProfileUpdate
from sift.services.dashboard_service import DashboardValidationError, dashboard_service


@pytest.mark.asyncio
async def test_get_prioritization_profile_returns_defaults_for_new_user() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="dashboard-defaults@example.com")
        session.add(user)
        await session.commit()

        profile = await dashboard_service.get_prioritization_profile(session=session, user_id=user.id)

        assert profile.source_weights == {"feed": 40, "monitoring_stream": 60}
        assert profile.recency_horizon_hours == 24

    await engine.dispose()


@pytest.mark.asyncio
async def test_update_prioritization_profile_validates_weight_range() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="dashboard-invalid@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(DashboardValidationError, match="source weight"):
            await dashboard_service.update_prioritization_profile(
                session=session,
                user_id=user.id,
                payload=DashboardPriorityProfileUpdate(source_weights={"feed": 101}),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_update_prioritization_profile_persists_user_scoped_values() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="dashboard-persist@example.com")
        other_user = User(email="dashboard-other@example.com")
        session.add_all([user, other_user])
        await session.commit()

        updated = await dashboard_service.update_prioritization_profile(
            session=session,
            user_id=user.id,
            payload=DashboardPriorityProfileUpdate(
                source_weights={"feed": 25, "monitoring_stream": 80},
                recency_horizon_hours=72,
            ),
        )
        other_profile = await dashboard_service.get_prioritization_profile(session=session, user_id=other_user.id)

        assert updated.source_weights == {"feed": 25, "monitoring_stream": 80}
        assert updated.recency_horizon_hours == 72
        assert other_profile.source_weights == {"feed": 40, "monitoring_stream": 60}
        assert other_profile.recency_horizon_hours == 24

        rows = await session.execute(select(UserPrioritizationProfile))
        persisted = rows.scalars().all()
        assert len(persisted) == 1
        assert persisted[0].user_id == user.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_prioritized_queue_ranks_unread_recent_monitoring_matches_first() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        now = datetime.now(UTC)
        user = User(email="dashboard-queue@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Security Feed", url="https://dashboard-queue.example.com/rss")
        session.add(feed)
        await session.flush()

        regular_article = Article(
            feed_id=feed.id,
            source_id="regular",
            title="General industry update",
            content_text="general news",
            published_at=now - timedelta(hours=1),
        )
        monitoring_article = Article(
            feed_id=feed.id,
            source_id="monitoring",
            title="Critical vulnerability exploited",
            content_text="security incident",
            published_at=now - timedelta(hours=2),
        )
        session.add_all([regular_article, monitoring_article])
        await session.flush()

        stream = KeywordStream(user_id=user.id, name="Security", match_query="vulnerability", priority=10)
        session.add(stream)
        await session.flush()
        session.add(KeywordStreamMatch(stream_id=stream.id, article_id=monitoring_article.id, matched_at=now))
        await session.commit()

        queue = await dashboard_service.get_prioritized_queue(session=session, user_id=user.id, limit=10)

        assert queue.status == "ready"
        assert [item.article_id for item in queue.items] == [monitoring_article.id, regular_article.id]
        assert queue.items[0].score_breakdown["monitoring_signal_bonus"] > 0
        assert any("Security" in reason for reason in queue.items[0].why_prioritized)

    await engine.dispose()


@pytest.mark.asyncio
async def test_prioritized_queue_excludes_read_and_archived_articles() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="dashboard-queue-filter@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Filter Feed", url="https://dashboard-queue-filter.example.com/rss")
        session.add(feed)
        await session.flush()

        unread_article = Article(feed_id=feed.id, source_id="unread", title="Unread", content_text="body")
        read_article = Article(feed_id=feed.id, source_id="read", title="Read", content_text="body")
        archived_article = Article(feed_id=feed.id, source_id="archived", title="Archived", content_text="body")
        session.add_all([unread_article, read_article, archived_article])
        await session.flush()
        session.add_all(
            [
                ArticleState(user_id=str(user.id), article_id=read_article.id, is_read=True),
                ArticleState(user_id=str(user.id), article_id=archived_article.id, is_archived=True),
            ]
        )
        await session.commit()

        queue = await dashboard_service.get_prioritized_queue(session=session, user_id=user.id, limit=10)

        assert [item.article_id for item in queue.items] == [unread_article.id]

    await engine.dispose()


@pytest.mark.asyncio
async def test_feed_health_card_counts_stale_and_error_feeds() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        now = datetime.now(UTC)
        user = User(email="dashboard-feed-health@example.com")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                Feed(
                    owner_id=user.id,
                    title="Stale Feed",
                    url="https://dashboard-feed-health.example.com/stale.xml",
                    fetch_interval_minutes=15,
                    last_fetch_success_at=now - timedelta(hours=8),
                ),
                Feed(
                    owner_id=user.id,
                    title="Error Feed",
                    url="https://dashboard-feed-health.example.com/error.xml",
                    last_fetch_success_at=now - timedelta(hours=1),
                    last_fetch_error="timeout",
                    last_fetch_error_at=now,
                ),
                Feed(
                    owner_id=user.id,
                    title="Healthy Feed",
                    url="https://dashboard-feed-health.example.com/healthy.xml",
                    last_fetch_success_at=now,
                ),
            ]
        )
        await session.commit()

        card = await dashboard_service.get_feed_health_card(session=session, user_id=user.id)

        assert card.status == "ready"
        assert card.stale_feed_count == 1
        assert card.error_feed_count == 1
        assert card.oldest_success_age_hours is not None
        assert card.oldest_success_age_hours >= 7.9
        assert card.queue_lag.unavailable_reason == "Worker queue metrics are not available yet."

    await engine.dispose()


@pytest.mark.asyncio
async def test_saved_followup_card_returns_starred_articles() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="dashboard-saved@example.com")
        session.add(user)
        await session.flush()
        feed = Feed(owner_id=user.id, title="Saved Feed", url="https://dashboard-saved.example.com/rss")
        session.add(feed)
        await session.flush()
        saved_article = Article(feed_id=feed.id, source_id="saved", title="Saved item", content_text="body")
        unsaved_article = Article(feed_id=feed.id, source_id="unsaved", title="Unsaved item", content_text="body")
        session.add_all([saved_article, unsaved_article])
        await session.flush()
        session.add(ArticleState(user_id=str(user.id), article_id=saved_article.id, is_starred=True))
        await session.commit()

        card = await dashboard_service.get_saved_followup_card(session=session, user_id=user.id, limit=5)

        assert card.status == "ready"
        assert card.saved_count == 1
        assert [item.article_id for item in card.latest_items] == [saved_article.id]
        assert card.latest_items[0].title == "Saved item"
        assert card.latest_items[0].feed_title == "Saved Feed"
        assert card.latest_items[0].saved_at is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_monitoring_signals_card_scores_streams_by_recent_matches_and_unread() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        now = datetime.now(UTC)
        user = User(email="dashboard-signals@example.com")
        session.add(user)
        await session.flush()
        feed = Feed(owner_id=user.id, title="Signals Feed", url="https://dashboard-signals.example.com/rss")
        session.add(feed)
        await session.flush()
        article = Article(feed_id=feed.id, source_id="signal", title="Signal article", content_text="body")
        session.add(article)
        await session.flush()
        hot_stream = KeywordStream(user_id=user.id, name="Hot Stream", match_query="signal", priority=10)
        cold_stream = KeywordStream(user_id=user.id, name="Cold Stream", match_query="cold", priority=100)
        session.add_all([hot_stream, cold_stream])
        await session.flush()
        session.add(KeywordStreamMatch(stream_id=hot_stream.id, article_id=article.id, matched_at=now))
        await session.commit()

        card = await dashboard_service.get_monitoring_signals_card(session=session, user_id=user.id, window_hours=24)

        assert card.status == "ready"
        assert card.window_hours == 24
        assert [stream.stream_id for stream in card.streams] == [hot_stream.id, cold_stream.id]
        assert card.streams[0].signal_score > card.streams[1].signal_score
        assert card.streams[0].matched_count_window == 1
        assert card.streams[0].unread_count_window == 1
        assert card.streams[0].score_breakdown["recent_matches"] > 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_discovery_candidates_card_returns_pending_recommendations() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        now = datetime.now(UTC)
        user = User(email="dashboard-discovery@example.com")
        session.add(user)
        await session.flush()
        pending_rec = FeedRecommendation(
            user_id=user.id,
            status="pending",
            feed_url="https://dashboard-discovery.example.com/feed.xml",
            feed_url_normalized="https://dashboard-discovery.example.com/feed.xml",
            feed_title="Pending Discovery Feed",
            provider="searxng",
            evidence_json='{"query_variants": ["python"]}',
            last_seen_at=now,
        )
        accepted_rec = FeedRecommendation(
            user_id=user.id,
            status="accepted",
            feed_url="https://dashboard-discovery.example.com/accepted.xml",
            feed_url_normalized="https://dashboard-discovery.example.com/accepted.xml",
            feed_title="Accepted Feed",
            provider="searxng",
            decided_at=now,
        )
        session.add_all([pending_rec, accepted_rec])
        await session.flush()
        await session.commit()

        card = await dashboard_service.get_discovery_candidates_card(session=session, user_id=user.id, limit=5)

        assert card.status == "ready"
        assert card.pending_recommendation_count == 1
        assert card.monitoring_candidate_count == 0
        assert len(card.candidates) == 1
        assert card.candidates[0].title == "Pending Discovery Feed"
        assert card.candidates[0].source_kind == "feed_recommendation"
        assert card.candidates[0].recommendation_id == pending_rec.id
        assert card.candidates[0].candidate_score > 0
        assert "Pending feed recommendation" in card.candidates[0].why_candidate[0]

    await engine.dispose()


@pytest.mark.asyncio
async def test_trends_card_detects_momentum_for_frequent_recent_keywords() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        now = datetime.now(UTC)
        user = User(email="dashboard-trends@example.com")
        session.add(user)
        await session.flush()
        feed = Feed(owner_id=user.id, title="Trends Feed", url="https://dashboard-trends.example.com/rss")
        session.add(feed)
        await session.flush()
        # Recent articles in short window — repeated keyword "rust"
        for i in range(5):
            session.add(
                Article(
                    feed_id=feed.id,
                    source_id=f"recent-{i}",
                    title=f"Rust release update {i}",
                    content_text="body",
                    published_at=now - timedelta(hours=2),
                )
            )
        # Old articles in baseline — no "rust" mentions
        for i in range(3):
            session.add(
                Article(
                    feed_id=feed.id,
                    source_id=f"old-{i}",
                    title=f"Generic news {i}",
                    content_text="body",
                    published_at=now - timedelta(days=10),
                )
            )
        await session.commit()

        card = await dashboard_service.get_trends_card(
            session=session, user_id=user.id, window_hours=24, baseline_days=14
        )

        assert card.status == "ready"
        assert card.window_hours == 24
        assert card.baseline_days == 14
        assert len(card.topics) > 0
        rust_topic = next((t for t in card.topics if "rust" in t.topic.lower()), None)
        assert rust_topic is not None
        assert rust_topic.short_window_count >= 5
        assert rust_topic.momentum_score > 0
        assert rust_topic.baseline_count == 0
        assert len(rust_topic.representative_article_ids) > 0

    await engine.dispose()
