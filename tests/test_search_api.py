from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from sift.api.deps.auth import get_current_user
from sift.config import get_settings
from sift.db.models import User
from sift.main import app
from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult
from sift.plugins.manager import PluginStatusSnapshot


class _SearchPluginManagerStub:
    def __init__(self, *, loaded: bool = True) -> None:
        self._loaded = loaded

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


def _write_search_registry(path: Path) -> None:
    path.write_text(
        """
version: 1
plugins:
  - id: search_provider
    enabled: true
    backend:
      class_path: sift.plugins.builtin.search_provider_noop:SearchProviderNoopPlugin
    capabilities:
      - search_provider
    settings:
      search_provider:
        provider_chain:
          - searxng
          - brave_search
        provider_budgets:
          searxng:
            max_requests_per_run: 10
            max_requests_per_day: 100
            min_interval_ms: 250
            max_query_variants_per_stream: 5
            max_results_per_query: 25
          brave_search:
            max_requests_per_run: 5
            max_requests_per_day: 25
            min_interval_ms: 400
            max_query_variants_per_stream: 4
            max_results_per_query: 10
""".strip(),
        encoding="utf-8",
    )


def test_search_providers_returns_configured_chain(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "plugins.yaml"
    _write_search_registry(registry_path)

    async def override_current_user() -> User:
        return User(email="search-user@example.com", is_admin=False)

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.api.routes.search.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=True))
    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("SIFT_PLUGIN_TIMEOUT_SEARCH_PROVIDER_MS", "7000")
    get_settings.cache_clear()

    from sift.core.runtime import get_plugin_manager

    get_plugin_manager.cache_clear()
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
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_plugin_manager.cache_clear()


def test_search_feeds_returns_ephemeral_candidates(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "plugins.yaml"
    _write_search_registry(registry_path)

    async def override_current_user() -> User:
        return User(email="search-user@example.com", is_admin=False)

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.api.routes.search.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=True))
    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()

    from sift.core.runtime import get_plugin_manager

    get_plugin_manager.cache_clear()
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
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_plugin_manager.cache_clear()


def test_search_providers_returns_503_when_plugin_unavailable(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "plugins.yaml"
    _write_search_registry(registry_path)

    async def override_current_user() -> User:
        return User(email="search-user@example.com", is_admin=False)

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.api.routes.search.get_plugin_manager", lambda: _SearchPluginManagerStub(loaded=False))
    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()

    from sift.core.runtime import get_plugin_manager

    get_plugin_manager.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/search/providers")
            assert response.status_code == 503
            assert response.json()["detail"] == "Search provider plugin unavailable"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        get_plugin_manager.cache_clear()
