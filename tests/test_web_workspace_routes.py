from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.config import get_settings
from sift.db.base import Base
from sift.db.models import User
from sift.db.session import get_db_session
from sift.main import app
from sift.web import routes as web_routes


def test_workspace_routes_auth_guard_and_redirects(monkeypatch) -> None:
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

            react_redirect = client.get("/app-react", follow_redirects=False)
            assert react_redirect.status_code == 307
            assert react_redirect.headers["location"] == "/app"

            cookie_name = get_settings().auth_session_cookie_name
            client.cookies.set(cookie_name, "test-token")
            authed_home = client.get("/app")
            assert authed_home.status_code == 200
            assert "Sift Workspace" in authed_home.text
            assert "react-workspace-root" in authed_home.text

            authed_react_home = client.get("/app-react", follow_redirects=False)
            assert authed_react_home.status_code == 307
            assert authed_react_home.headers["location"] == "/app"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
