from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import Article, ArticleState, Feed, User
from sift.db.session import get_db_session
from sift.main import app


def test_feed_health_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/feeds/health")
        assert response.status_code == 401


def test_feed_health_api_lifecycle_and_settings_flow() -> None:
    db_path = Path("test_feed_health_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> tuple[User, Feed]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            user = User(email="feed-health-api@example.com")
            session.add(user)
            await session.flush()

            feed = Feed(
                owner_id=user.id,
                title="API Feed",
                url="https://feed-health-api.example.com/rss",
                fetch_interval_minutes=30,
                is_active=True,
                last_fetch_success_at=datetime.now(UTC) - timedelta(hours=12),
            )
            session.add(feed)
            await session.flush()

            article = Article(feed_id=feed.id, source_id="a1", title="Unread article", content_text="body")
            session.add(article)
            await session.commit()
            return user, feed

    import asyncio

    user, feed = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            health_response = client.get(
                "/api/v1/feeds/health",
                params={"lifecycle": "active", "stale_only": "true", "limit": "50", "offset": "0"},
            )
            assert health_response.status_code == 200
            health_payload = health_response.json()
            assert health_payload["total"] == 1
            assert health_payload["items"][0]["feed_id"] == str(feed.id)
            assert health_payload["items"][0]["lifecycle_status"] == "active"
            assert health_payload["items"][0]["is_stale"] is True
            assert health_payload["summary"]["total_feed_count"] == 1

            settings_response = client.patch(
                f"/api/v1/feeds/{feed.id}/settings",
                json={"fetch_interval_minutes": 120},
            )
            assert settings_response.status_code == 200
            assert settings_response.json()["fetch_interval_minutes"] == 120

            invalid_settings_response = client.patch(
                f"/api/v1/feeds/{feed.id}/settings",
                json={"fetch_interval_minutes": 0},
            )
            assert invalid_settings_response.status_code == 400

            archive_response = client.patch(
                f"/api/v1/feeds/{feed.id}/lifecycle",
                json={"action": "archive"},
            )
            assert archive_response.status_code == 200
            archive_payload = archive_response.json()
            assert archive_payload["marked_read_count"] == 1
            assert archive_payload["feed"]["is_archived"] is True
            assert archive_payload["feed"]["is_active"] is False

            feeds_response = client.get("/api/v1/feeds")
            assert feeds_response.status_code == 200
            assert feeds_response.json() == []

            include_archived_response = client.get("/api/v1/feeds", params={"include_archived": "true"})
            assert include_archived_response.status_code == 200
            assert len(include_archived_response.json()) == 1

            unarchive_response = client.patch(
                f"/api/v1/feeds/{feed.id}/lifecycle",
                json={"action": "unarchive"},
            )
            assert unarchive_response.status_code == 200
            unarchive_payload = unarchive_response.json()
            assert unarchive_payload["marked_read_count"] == 0
            assert unarchive_payload["feed"]["is_archived"] is False
            assert unarchive_payload["feed"]["is_active"] is True

        async def verify_read_state() -> None:
            async with session_maker() as session:
                state_rows = await session.execute(
                    select(ArticleState).where(ArticleState.user_id == str(user.id))
                )
                states = state_rows.scalars().all()
                assert len(states) == 1
                assert states[0].is_read is True

        asyncio.run(verify_read_state())
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
