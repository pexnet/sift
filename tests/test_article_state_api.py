from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import Article, Feed, User
from sift.db.session import get_db_session
from sift.main import app


def test_article_state_api_patch_and_bulk() -> None:
    db_path = Path("test_article_state_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> tuple[User, Article, Article]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            user = User(email="api-state@example.com")
            other = User(email="api-state-other@example.com")
            session.add_all([user, other])
            await session.flush()

            feed = Feed(owner_id=user.id, title="Owned Feed", url="https://api-state-owned.example.com/rss")
            other_feed = Feed(owner_id=other.id, title="Other Feed", url="https://api-state-other.example.com/rss")
            session.add_all([feed, other_feed])
            await session.flush()

            owned_article = Article(feed_id=feed.id, source_id="a1", title="Owned", content_text="Body")
            other_article = Article(feed_id=other_feed.id, source_id="a2", title="Other", content_text="Body")
            session.add_all([owned_article, other_article])
            await session.commit()
            return user, owned_article, other_article

    import asyncio

    user, owned_article, other_article = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            patch_response = client.patch(
                f"/api/v1/articles/{owned_article.id}/state",
                json={"is_read": True},
            )
            assert patch_response.status_code == 200
            assert patch_response.json()["is_read"] is True

            bulk_response = client.post(
                "/api/v1/articles/state/bulk",
                json={
                    "article_ids": [str(owned_article.id), str(other_article.id)],
                    "is_starred": True,
                },
            )
            assert bulk_response.status_code == 200
            assert bulk_response.json()["updated_count"] == 1
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
