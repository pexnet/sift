from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import Article, Feed, KeywordStreamMatch, User
from sift.db.session import get_db_session
from sift.domain.schemas import KeywordStreamCreate
from sift.main import app
from sift.services.stream_service import stream_service


def test_stream_backfill_api_runs_and_replaces_matches() -> None:
    db_path = Path("test_stream_backfill_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> tuple[User, UUID, UUID]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            user = User(email="api-stream-backfill@example.com")
            session.add(user)
            await session.flush()

            feed = Feed(owner_id=user.id, title="Owned Feed", url="https://api-stream-backfill.example.com/rss")
            session.add(feed)
            await session.flush()

            matching_article = Article(
                feed_id=feed.id,
                source_id="a1",
                title="Microsoft Sentinel alert",
                content_text="security monitoring",
            )
            stale_article = Article(
                feed_id=feed.id,
                source_id="a2",
                title="Football summary",
                content_text="sports roundup",
            )
            session.add_all([matching_article, stale_article])
            await session.flush()

            stream = await stream_service.create_stream(
                session=session,
                user_id=user.id,
                payload=KeywordStreamCreate(name="security", match_query="microsoft AND NOT sports"),
            )
            session.add(KeywordStreamMatch(stream_id=stream.id, article_id=stale_article.id))
            await session.commit()
            return user, stream.id, matching_article.id

    import asyncio

    user, stream_id, matching_article_id = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.post(f"/api/v1/streams/{stream_id}/backfill", json={})
            assert response.status_code == 200
            payload = response.json()
            assert payload["stream_id"] == str(stream_id)
            assert payload["scanned_count"] == 2
            assert payload["previous_match_count"] == 1
            assert payload["matched_count"] == 1

        async def verify() -> None:
            async with session_maker() as session:
                result = await session.execute(
                    select(KeywordStreamMatch).where(KeywordStreamMatch.stream_id == stream_id)
                )
                rows = result.scalars().all()
                assert len(rows) == 1
                assert rows[0].article_id == matching_article_id

        asyncio.run(verify())
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
