from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.config import get_settings
from sift.db.base import Base
from sift.db.models import User
from sift.db.session import get_db_session
from sift.main import app
from sift.plugins.manager import PluginStatusSnapshot


class _PluginManagerStub:
    def get_status_snapshots(self) -> list[PluginStatusSnapshot]:
        return [
            PluginStatusSnapshot(
                plugin_id="noop",
                enabled=True,
                loaded=True,
                capabilities=["ingest_hook"],
                startup_validation_status="ok",
                last_error=None,
                unavailable_reason=None,
                runtime_counters={
                    "ingest_hook": {
                        "success_count": 2,
                        "failure_count": 1,
                        "timeout_count": 0,
                    }
                },
                last_updated_at=datetime.now(UTC),
            )
        ]


def test_plugins_status_requires_admin_and_returns_shape(monkeypatch) -> None:
    db_path = Path("test_plugins_api.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    import asyncio

    async def prepare() -> tuple[User, User]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            admin = User(email="plugin-admin@example.com", is_admin=True)
            non_admin = User(email="plugin-user@example.com", is_admin=False)
            session.add(admin)
            session.add(non_admin)
            await session.commit()
            return admin, non_admin

    admin, non_admin = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    monkeypatch.setattr("sift.api.routes.plugins.get_plugin_manager", lambda: _PluginManagerStub())

    async def override_admin_user() -> User:
        return admin

    async def override_non_admin_user() -> User:
        return non_admin

    get_settings.cache_clear()

    try:
        app.dependency_overrides[get_current_user] = override_admin_user
        with TestClient(app) as client:
            response = client.get("/api/v1/plugins/status")
            assert response.status_code == 200
            payload = response.json()
            assert len(payload) == 1
            assert payload[0]["plugin_id"] == "noop"
            assert payload[0]["loaded"] is True
            assert payload[0]["runtime_counters"]["ingest_hook"]["success_count"] == 2

        app.dependency_overrides[get_current_user] = override_non_admin_user
        with TestClient(app) as client:
            response = client.get("/api/v1/plugins/status")
            assert response.status_code == 403
            assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_plugins_status_returns_404_when_diagnostics_disabled(monkeypatch) -> None:
    db_path = Path("test_plugins_api_diagnostics_off.db")
    if db_path.exists():
        db_path.unlink()

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    import asyncio

    async def prepare() -> User:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            admin = User(email="plugin-admin-off@example.com", is_admin=True)
            session.add(admin)
            await session.commit()
            return admin

    admin = asyncio.run(prepare())

    async def override_db_session():
        async with session_maker() as session:
            yield session

    async def override_admin_user() -> User:
        return admin

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_admin_user
    monkeypatch.setattr("sift.api.routes.plugins.get_plugin_manager", lambda: _PluginManagerStub())
    monkeypatch.setenv("SIFT_PLUGIN_DIAGNOSTICS_ENABLED", "false")
    get_settings.cache_clear()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/plugins/status")
            assert response.status_code == 404
            assert response.json()["detail"] == "Plugin diagnostics disabled"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
