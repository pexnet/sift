from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.config import get_settings
from sift.db.base import Base
from sift.db.models import User
from sift.db.session import get_db_session
from sift.main import app
from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult
from sift.plugins.manager import PluginStatusSnapshot
from sift.plugins.registry import PluginBackendConfig, PluginRegistryEntry
from sift.services.search_service import search_provider_service


class _SearchPluginManagerStub:
    def __init__(self, *, loaded: bool = True) -> None:
        self._loaded = loaded
        self._registry_entries = [
            PluginRegistryEntry(
                id="search_provider",
                enabled=True,
                backend=PluginBackendConfig(class_path="sift.plugins.builtin.search_provider_noop:SearchProviderNoopPlugin"),
                capabilities=["search_provider"],
                settings={
                    "search_provider": {
                        "provider_chain": ["searxng", "brave_search"],
                        "provider_budgets": {
                            "searxng": {
                                "max_requests_per_run": 10,
                                "max_requests_per_day": 100,
                                "min_interval_ms": 250,
                                "max_query_variants_per_stream": 5,
                                "max_results_per_query": 25,
                            },
                            "brave_search": {
                                "max_requests_per_run": 5,
                                "max_requests_per_day": 25,
                                "min_interval_ms": 400,
                                "max_query_variants_per_stream": 4,
                                "max_results_per_query": 10,
                            },
                        },
                    }
                },
            )
        ]

    def get_status_snapshots(self) -> list[PluginStatusSnapshot]:
        return [
            PluginStatusSnapshot(
                plugin_id="search_provider",
                enabled=True,
                loaded=self._loaded,
                capabilities=["search_provider"],
                startup_validation_status="ok" if self._loaded else "load_error",
                last_error=None if self._loaded else "load failed",
                unavailable_reason=None if self._loaded else "load failed",
                runtime_counters={},
                last_updated_at=datetime.now(UTC),
            )
        ]

    def get_registry_entries(self) -> list[PluginRegistryEntry]:
        return [item.model_copy(deep=True) for item in self._registry_entries]

    async def search_feeds(self, *, plugin_name: str, request: SearchFeedsRequest) -> SearchFeedsResult | None:
        del plugin_name
        provider = request.provider_chain[0] if request.provider_chain else "searxng"
        return SearchFeedsResult(
            provider=provider,
            candidates=[
                SearchFeedCandidate(
                    title=f"{request.query} blog",
                    url="https://example.com/feed.xml",
                    site_url="https://example.com",
                    description="example candidate",
                    provider=provider,
                )
            ],
            warnings=[],
        )


def _prepare_test_db(db_path: Path) -> tuple[AsyncEngine, async_sessionmaker]:
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
    return engine, session_maker


def test_search_providers_returns_configured_chain(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test_search_api_providers.db"
    engine, session_maker = _prepare_test_db(db_path)

    async def override_db_session() -> AsyncGenerator[object]:
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return User(email="search-user@example.com", is_admin=False)

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.api.routes.search.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=True))
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=True))
    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(tmp_path / "missing-registry.yaml"))
    monkeypatch.setenv("SIFT_PLUGIN_TIMEOUT_SEARCH_PROVIDER_MS", "7000")
    get_settings.cache_clear()

    from sift.core.runtime import get_plugin_manager

    get_plugin_manager.cache_clear()
    search_provider_service.reset_budget_state()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/search/providers")
            assert response.status_code == 200
            payload = response.json()
            assert payload["plugin_id"] == "search_provider"
            assert payload["provider_chain"] == ["searxng", "brave_search"]
            assert payload["provider_budgets"]["searxng"]["max_requests_per_run"] == 10
            assert payload["timeout_ms"] == 7000
            assert payload["loaded"] is True
    finally:
        import asyncio

        search_provider_service.reset_budget_state()
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_plugin_manager.cache_clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_search_feeds_returns_ephemeral_candidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test_search_api_feeds.db"
    engine, session_maker = _prepare_test_db(db_path)

    async def override_db_session() -> AsyncGenerator[object]:
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return User(email="search-user@example.com", is_admin=False)

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.api.routes.search.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=True))
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=True))
    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(tmp_path / "missing-registry.yaml"))
    get_settings.cache_clear()

    from sift.core.runtime import get_plugin_manager

    get_plugin_manager.cache_clear()
    search_provider_service.reset_budget_state()
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/search/feeds", json={"query": "ai research", "max_results": 10})
            assert response.status_code == 200
            payload = response.json()
            assert payload["query"] == "ai research"
            assert payload["provider"] == "searxng"
            assert payload["provider_chain"] == ["searxng", "brave_search"]
            assert len(payload["candidates"]) == 1
            assert payload["candidates"][0]["url"] == "https://example.com/feed.xml"
            assert payload["warning_details"] == []
    finally:
        import asyncio

        search_provider_service.reset_budget_state()
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_plugin_manager.cache_clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_search_providers_returns_503_when_plugin_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test_search_api_unavailable.db"
    engine, session_maker = _prepare_test_db(db_path)

    async def override_db_session() -> AsyncGenerator[object]:
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return User(email="search-user@example.com", is_admin=False)

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.api.routes.search.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=False))
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=False))
    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(tmp_path / "missing-registry.yaml"))
    get_settings.cache_clear()

    from sift.core.runtime import get_plugin_manager

    get_plugin_manager.cache_clear()
    search_provider_service.reset_budget_state()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/search/providers")
            assert response.status_code == 503
            assert response.json()["detail"] == "Search provider plugin unavailable"
    finally:
        import asyncio

        search_provider_service.reset_budget_state()
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_plugin_manager.cache_clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
