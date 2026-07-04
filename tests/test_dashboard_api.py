import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import Article, ArticleState, Feed, KeywordStream, KeywordStreamMatch, User
from sift.db.session import get_db_session
from sift.main import app


def _dashboard_api_db_path(name: str) -> Path:
    db_path = Path(name)
    if db_path.exists():
        db_path.unlink()
    return db_path


async def _prepare_dashboard_api_user(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    email: str,
) -> User:
    async with session_maker() as session:
        user = User(email=email)
        session.add(user)
        await session.commit()
        return user


def test_dashboard_summary_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/summary")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"


def test_dashboard_summary_returns_card_availability_for_authenticated_user() -> None:
    async def override_current_user() -> User:
        return User(email="dashboard-user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/summary")
            assert response.status_code == 200
            payload = response.json()
            assert "last_updated_at" in payload
            assert len(payload["cards"]) >= 1
            by_id = {item["id"]: item for item in payload["cards"]}
            assert by_id["saved_followup"]["status"] == "ready"
            assert by_id["trends"]["status"] == "ready"
            assert by_id["discovery_candidates"]["status"] == "ready"
    finally:
        app.dependency_overrides.clear()


def test_dashboard_prioritization_profile_requires_auth() -> None:
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/prioritization-profile")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"
    finally:
        client.close()


def test_dashboard_prioritization_profile_returns_defaults_for_user() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_profile_defaults.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return await _prepare_dashboard_api_user(session_maker, email="dashboard-profile-defaults@example.com")

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/prioritization-profile")
        assert response.status_code == 200
        assert response.json() == {
            "source_weights": {"feed": 40, "monitoring_stream": 60},
            "recency_horizon_hours": 24,
        }
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_prioritization_profile_update_persists_values() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_profile_update.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return await _prepare_dashboard_api_user(session_maker, email="dashboard-profile-update@example.com")

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        patch_response = client.patch(
            "/api/v1/dashboard/prioritization-profile",
            json={
                "source_weights": {"feed": 25, "monitoring_stream": 80},
                "recency_horizon_hours": 72,
            },
        )
        assert patch_response.status_code == 200
        assert patch_response.json() == {
            "source_weights": {"feed": 25, "monitoring_stream": 80},
            "recency_horizon_hours": 72,
        }

        get_response = client.get("/api/v1/dashboard/prioritization-profile")
        assert get_response.status_code == 200
        assert get_response.json() == patch_response.json()
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_prioritization_profile_update_rejects_bad_weight() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_profile_invalid.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return await _prepare_dashboard_api_user(session_maker, email="dashboard-profile-invalid@example.com")

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.patch(
            "/api/v1/dashboard/prioritization-profile",
            json={"source_weights": {"feed": 101}},
        )
        assert response.status_code == 400
        assert "source weight" in response.json()["detail"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_prioritized_queue_returns_ranked_items() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_prioritized_queue.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            user = User(email="dashboard-queue-api@example.com")
            session.add(user)
            await session.flush()
            feed = Feed(owner_id=user.id, title="Queue Feed", url="https://dashboard-queue-api.example.com/rss")
            session.add(feed)
            await session.flush()
            article = Article(
                feed_id=feed.id,
                source_id="queue-1",
                title="Critical dashboard incident",
                content_text="incident details",
                published_at=datetime.now(UTC),
            )
            session.add(article)
            await session.flush()
            stream = KeywordStream(user_id=user.id, name="Incidents", match_query="incident")
            session.add(stream)
            await session.flush()
            session.add(KeywordStreamMatch(stream_id=stream.id, article_id=article.id))
            await session.commit()
            return user

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/cards/prioritized-queue")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["profile"]["source_weights"] == {"feed": 40, "monitoring_stream": 60}
        assert len(payload["items"]) == 1
        assert payload["items"][0]["title"] == "Critical dashboard incident"
        assert payload["items"][0]["score_breakdown"]["monitoring_signal_bonus"] == 60
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_feed_health_card_returns_counts() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_feed_health_card.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            user = User(email="dashboard-feed-health-api@example.com")
            session.add(user)
            await session.flush()
            session.add(
                Feed(
                    owner_id=user.id,
                    title="Broken Feed",
                    url="https://dashboard-feed-health-api.example.com/rss",
                    last_fetch_success_at=datetime.now(UTC),
                    last_fetch_error="timeout",
                )
            )
            await session.commit()
            return user

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/cards/feed-health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["stale_feed_count"] == 0
        assert payload["error_feed_count"] == 1
        assert payload["queue_lag"]["unavailable_reason"] == "Worker queue metrics are not available yet."
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_saved_followup_card_returns_starred_items() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_saved_followup_card.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            user = User(email="dashboard-saved-api@example.com")
            session.add(user)
            await session.flush()
            feed = Feed(owner_id=user.id, title="Saved API Feed", url="https://dashboard-saved-api.example.com/rss")
            session.add(feed)
            await session.flush()
            article = Article(feed_id=feed.id, source_id="saved-api", title="Saved API item", content_text="body")
            session.add(article)
            await session.flush()
            session.add(ArticleState(user_id=str(user.id), article_id=article.id, is_starred=True))
            await session.commit()
            return user

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/cards/saved-followup")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["saved_count"] == 1
        assert payload["latest_items"][0]["title"] == "Saved API item"
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_monitoring_signals_card_returns_stream_scores() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_monitoring_signals_card.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            user = User(email="dashboard-signals-api@example.com")
            session.add(user)
            await session.flush()
            feed = Feed(owner_id=user.id, title="Signals API Feed", url="https://dashboard-signals-api.example.com/rss")
            session.add(feed)
            await session.flush()
            article = Article(feed_id=feed.id, source_id="signal-api", title="Signal API item", content_text="body")
            session.add(article)
            await session.flush()
            stream = KeywordStream(user_id=user.id, name="Signals API", match_query="signal")
            session.add(stream)
            await session.flush()
            session.add(KeywordStreamMatch(stream_id=stream.id, article_id=article.id, matched_at=datetime.now(UTC)))
            await session.commit()
            return user

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/cards/monitoring-signals")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["window_hours"] == 24
        assert payload["streams"][0]["stream_name"] == "Signals API"
        assert payload["streams"][0]["matched_count_window"] == 1
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_discovery_candidates_card_returns_pending_recommendations() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_discovery_candidates_card.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            user = User(email="dashboard-discovery-api@example.com")
            session.add(user)
            await session.flush()
            from sift.db.models import FeedRecommendation

            session.add(
                FeedRecommendation(
                    user_id=user.id,
                    status="pending",
                    feed_url="https://dashboard-discovery-api.example.com/feed.xml",
                    feed_url_normalized="https://dashboard-discovery-api.example.com/feed.xml",
                    feed_title="Pending API Feed",
                    provider="searxng",
                )
            )
            await session.commit()
            return user

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/cards/discovery-candidates")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["pending_recommendation_count"] == 1
        assert payload["monitoring_candidate_count"] == 0
        assert payload["candidates"][0]["title"] == "Pending API Feed"
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_dashboard_trends_card_returns_topics() -> None:
    db_path = _dashboard_api_db_path("test_dashboard_trends_card.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            user = User(email="dashboard-trends-api@example.com")
            session.add(user)
            await session.flush()
            feed = Feed(owner_id=user.id, title="Trends API Feed", url="https://dashboard-trends-api.example.com/rss")
            session.add(feed)
            await session.flush()
            for i in range(3):
                session.add(
                    Article(
                        feed_id=feed.id,
                        source_id=f"trend-{i}",
                        title=f"Rust async runtime {i}",
                        content_text="body",
                        published_at=datetime.now(UTC) - timedelta(hours=2),
                    )
                )
            await session.commit()
            return user

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)
    try:
        response = client.get("/api/v1/dashboard/cards/trends")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["window_hours"] == 24
        assert payload["baseline_days"] == 14
        assert len(payload["topics"]) > 0
        assert any("rust" in t["topic"].lower() for t in payload["topics"])
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
