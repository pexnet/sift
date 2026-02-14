from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.config import get_settings
from sift.db.base import Base
from sift.db.models import Article, Feed, FeedFolder, User
from sift.db.session import get_db_session
from sift.main import app
from sift.web import routes as web_routes


def test_workspace_routes_auth_guard_and_partials(monkeypatch) -> None:
    db_path = Path("test_workspace_routes.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            user = User(email="workspace@example.com")
            session.add(user)
            await session.flush()

            folder = FeedFolder(user_id=user.id, name="Security")
            session.add(folder)
            await session.flush()

            feed = Feed(owner_id=user.id, folder_id=folder.id, title="Feed One", url="https://workspace.example.com/rss")
            session.add(feed)
            await session.flush()

            article = Article(feed_id=feed.id, source_id="w1", title="Workspace Article", content_text="Body")
            session.add(article)
            await session.commit()
            return user

    import asyncio

    user = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def fake_get_user_by_session_token(*, session, raw_token: str):  # noqa: ANN001
        if raw_token:
            return user
        return None

    monkeypatch.setattr(web_routes.auth_service, "get_user_by_session_token", fake_get_user_by_session_token)
    app.dependency_overrides[get_db_session] = override_db_session

    try:
        with TestClient(app) as client:
            unauth_home = client.get("/app", follow_redirects=False)
            assert unauth_home.status_code == 303
            assert unauth_home.headers["location"] == "/login"

            unauth_partial = client.get("/web/partials/nav-tree")
            assert unauth_partial.status_code == 401

            cookie_name = get_settings().auth_session_cookie_name
            client.cookies.set(cookie_name, "test-token")
            authed_home = client.get("/app")
            assert authed_home.status_code == 200
            assert "Newsfeed" in authed_home.text
            assert "Workspace Article" in authed_home.text

            authed_partial = client.get("/web/partials/nav-tree")
            assert authed_partial.status_code == 200
            assert "System" in authed_partial.text
            assert "Security" in authed_partial.text
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
