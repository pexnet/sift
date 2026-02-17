from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.session import get_db_session
from sift.main import app
from sift.services.auth_service import auth_service


def test_auth_me_returns_401_when_session_lookup_errors(monkeypatch) -> None:
    db_path = Path("test_auth_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    import asyncio

    async def prepare() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def raise_db_error(*_args, **_kwargs):
        raise SQLAlchemyError("session lookup failed")

    monkeypatch.setattr(auth_service, "get_user_by_session_token", raise_db_error)
    app.dependency_overrides[get_db_session] = override_db_session

    try:
        with TestClient(app) as client:
            client.cookies.set("sift_session", "test-token")
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid session"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
