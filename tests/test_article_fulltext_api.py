from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import Article, Feed, User
from sift.db.session import get_db_session
from sift.main import app
from sift.services.article_fulltext_service import article_fulltext_service


def test_article_fulltext_fetch_endpoint_success_and_detail_projection(monkeypatch) -> None:
    db_path = Path("test_article_fulltext_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    import asyncio

    async def prepare() -> tuple[User, Article]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            user = User(email="article-fulltext-api@example.com")
            session.add(user)
            await session.flush()

            feed = Feed(owner_id=user.id, title="Owned Feed", url="https://article-fulltext-api.example.com/rss")
            session.add(feed)
            await session.flush()

            article = Article(
                feed_id=feed.id,
                source_id="a1",
                title="Owned",
                content_text="Excerpt",
                canonical_url="https://example.com/article",
            )
            session.add(article)
            await session.commit()
            return user, article

    user, article = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    async def fake_fetch_source_page(url: str) -> tuple[str, str]:
        assert url == "https://example.com/article"
        return (
            "https://example.com/article",
            "<html><body><article><p>Fetched content.</p></article></body></html>",
        )

    monkeypatch.setattr(article_fulltext_service, "_fetch_source_page", fake_fetch_source_page)
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            fetch_response = client.post(f"/api/v1/articles/{article.id}/fulltext/fetch")
            assert fetch_response.status_code == 200
            payload = fetch_response.json()
            assert payload["article_id"] == str(article.id)
            assert payload["status"] == "succeeded"
            assert payload["content_source"] == "full_article"

            detail_response = client.get(f"/api/v1/articles/{article.id}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["fulltext_status"] == "succeeded"
            assert detail["content_source"] == "full_article"
            assert "Fetched content." in (detail["fulltext_content_text"] or "")
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_article_fulltext_fetch_endpoint_rejects_other_user_article() -> None:
    db_path = Path("test_article_fulltext_api_forbidden.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    import asyncio

    async def prepare() -> tuple[User, User, Article]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            owner = User(email="article-fulltext-owner@example.com")
            other = User(email="article-fulltext-other@example.com")
            session.add_all([owner, other])
            await session.flush()

            feed = Feed(owner_id=owner.id, title="Owner Feed", url="https://article-fulltext-owner.example.com/rss")
            session.add(feed)
            await session.flush()

            article = Article(
                feed_id=feed.id,
                source_id="a1",
                title="Owned",
                content_text="Excerpt",
                canonical_url="https://example.com/article",
            )
            session.add(article)
            await session.commit()
            return owner, other, article

    _owner, other, article = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return other

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            fetch_response = client.post(f"/api/v1/articles/{article.id}/fulltext/fetch")
            assert fetch_response.status_code == 404
            assert "not found" in fetch_response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
