import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from sift.api.deps.auth import get_current_user
from sift.db.base import Base
from sift.db.models import KeywordStream, User
from sift.db.session import get_db_session
from sift.main import app
from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult
from sift.plugins.manager import PluginStatusSnapshot
from sift.plugins.registry import PluginBackendConfig, PluginRegistryEntry


class _DiscoveryApiSearchManagerStub:
    def __init__(self, *, loaded: bool = True) -> None:
        self._loaded = loaded
        self.calls: list[str] = []
        self._registry_entries = [
            PluginRegistryEntry(
                id="search_provider",
                enabled=True,
                backend=PluginBackendConfig(
                    class_path="sift.plugins.builtin.search_provider_noop:SearchProviderNoopPlugin"
                ),
                capabilities=["search_provider"],
                settings={
                    "search_provider": {
                        "provider_chain": ["searxng"],
                        "provider_budgets": {
                            "searxng": {
                                "max_requests_per_run": 10,
                                "max_requests_per_day": 100,
                                "min_interval_ms": 1,
                                "max_query_variants_per_stream": 2,
                                "max_results_per_query": 25,
                            }
                        },
                        "providers": {
                            "searxng": {
                                "base_url": "http://localhost:8080/search",
                            }
                        },
                    }
                },
            )
        ]

    def get_registry_entries(self) -> list[PluginRegistryEntry]:
        return [item.model_copy(deep=True) for item in self._registry_entries]

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
        self.calls.append(request.query)
        return SearchFeedsResult(
            provider="searxng",
            candidates=[
                SearchFeedCandidate(
                    title=f"candidate: {request.query}",
                    url="https://example.com/feed.xml#dup",
                    site_url="https://example.com#home",
                    description="test candidate",
                    provider="searxng",
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


def _seed_user(*, session_maker: async_sessionmaker, email: str) -> User:
    import asyncio

    async def seed() -> User:
        async with session_maker() as session:
            user = User(email=email, is_admin=False)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return asyncio.run(seed())


def test_discovery_streams_crud_and_generate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test_discovery_api.db"
    engine, session_maker = _prepare_test_db(db_path)
    user = _seed_user(session_maker=session_maker, email="discovery-user@example.com")
    manager = _DiscoveryApiSearchManagerStub(loaded=True)

    async def override_db_session() -> AsyncGenerator[AsyncSession]:
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.services.discovery_service.get_plugin_manager", lambda: manager)
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)

    async def _resolve_feed_endpoint_stub(
        self: object,
        *,
        client: object,
        candidate: SearchFeedCandidate,
    ) -> str:
        del self, client
        return candidate.url

    monkeypatch.setattr(
        "sift.services.discovery_service.DiscoveryService._resolve_feed_endpoint_for_candidate",
        _resolve_feed_endpoint_stub,
    )

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/discovery/streams",
                json={"name": "Threat intel", "include_keywords": ["threat", "intel"], "exclude_keywords": ["jobs"]},
            )
            assert create_response.status_code == 201
            stream_payload = create_response.json()
            stream_id = stream_payload["id"]
            assert stream_payload["name"] == "Threat intel"
            assert stream_payload["include_keywords"] == ["threat", "intel"]

            list_response = client.get("/api/v1/discovery/streams")
            assert list_response.status_code == 200
            assert len(list_response.json()) == 1

            async def create_monitoring_stream() -> str:
                async with session_maker() as session:
                    stream = KeywordStream(
                        user_id=user.id,
                        name="Monitoring source",
                        description="copied description",
                        is_active=True,
                        priority=130,
                        match_query="threat AND intel",
                        include_keywords_json='["threat", "intel"]',
                        exclude_keywords_json='["jobs"]',
                        include_regex_json="[]",
                        exclude_regex_json="[]",
                        source_contains=None,
                        language_equals=None,
                        classifier_mode="rules_only",
                        classifier_plugin=None,
                        classifier_config_json="{}",
                        classifier_min_confidence=0.7,
                    )
                    session.add(stream)
                    await session.commit()
                    await session.refresh(stream)
                    return str(stream.id)

            monitoring_stream_id = asyncio.run(create_monitoring_stream())
            copy_response = client.post(
                "/api/v1/discovery/streams/copy-from-monitoring",
                json={"monitoring_stream_id": monitoring_stream_id},
            )
            assert copy_response.status_code == 201
            copied_stream = copy_response.json()
            assert copied_stream["name"] == "Monitoring source (discovery)"
            assert copied_stream["include_keywords"] == ["threat", "intel"]
            assert copied_stream["exclude_keywords"] == ["jobs"]
            assert copied_stream["match_query"] == "threat AND intel"

            generate_response = client.post(f"/api/v1/discovery/streams/{stream_id}/generate", json={})
            assert generate_response.status_code == 200
            generated = generate_response.json()
            assert generated["stream_id"] == stream_id
            assert generated["provider_chain"] == ["searxng"]
            assert generated["attempted_queries"] == 2
            assert generated["candidate_count"] == 1
            assert generated["persisted_count"] == 1
            assert generated["pending_count"] == 1
            assert generated["resolved_existing_count"] == 0
            assert generated["candidates"][0]["url"] == "https://example.com/feed.xml"
            assert generated["candidates"][0]["site_url"] == "https://example.com"

            recommendations_response = client.get("/api/v1/discovery/recommendations", params={"status": "pending"})
            assert recommendations_response.status_code == 200
            recommendations_payload = recommendations_response.json()
            assert recommendations_payload["total"] == 1
            assert len(recommendations_payload["items"]) == 1
            recommendation_id = recommendations_payload["items"][0]["id"]
            assert recommendations_payload["items"][0]["status"] == "pending"
            assert len(recommendations_payload["items"][0]["sources"]) == 1
            assert recommendations_payload["items"][0]["sources"][0]["discovery_stream_id"] == stream_id

            deny_response = client.patch(
                f"/api/v1/discovery/recommendations/{recommendation_id}",
                json={"decision": "deny"},
            )
            assert deny_response.status_code == 200
            assert deny_response.json()["status"] == "denied"

            summary_after_deny = client.get("/api/v1/discovery/recommendations/summary")
            assert summary_after_deny.status_code == 200
            assert summary_after_deny.json()["pending_count"] == 0
            assert summary_after_deny.json()["denied_count"] == 1

            reset_response = client.post(f"/api/v1/discovery/recommendations/{recommendation_id}/reset", json={})
            assert reset_response.status_code == 200
            assert reset_response.json()["status"] == "pending"

            accept_response = client.patch(
                f"/api/v1/discovery/recommendations/{recommendation_id}",
                json={"decision": "accept"},
            )
            assert accept_response.status_code == 200
            assert accept_response.json()["status"] == "accepted"
            assert accept_response.json()["accepted_feed_id"] is not None

            summary_after_accept = client.get("/api/v1/discovery/recommendations/summary")
            assert summary_after_accept.status_code == 200
            assert summary_after_accept.json()["pending_count"] == 0
            assert summary_after_accept.json()["accepted_count"] == 1

            denied_after_accept = client.patch(
                f"/api/v1/discovery/recommendations/{recommendation_id}",
                json={"decision": "deny"},
            )
            assert denied_after_accept.status_code == 400

            recommendations_sorted = client.get(
                "/api/v1/discovery/recommendations",
                params={"status": "accepted", "q": "example.com", "sort_by": "feed_title", "sort_direction": "asc"},
            )
            assert recommendations_sorted.status_code == 200
            sorted_payload = recommendations_sorted.json()
            assert sorted_payload["total"] == 1
            assert sorted_payload["items"][0]["status"] == "accepted"

            update_response = client.patch(
                f"/api/v1/discovery/streams/{stream_id}",
                json={"match_query": "threat AND intel"},
            )
            assert update_response.status_code == 200
            assert update_response.json()["match_query"] == "threat AND intel"

            delete_response = client.delete(f"/api/v1/discovery/streams/{stream_id}")
            assert delete_response.status_code == 204

            list_after_delete = client.get("/api/v1/discovery/streams")
            assert list_after_delete.status_code == 200
            assert len(list_after_delete.json()) == 1
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()


def test_discovery_generate_returns_503_when_plugin_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test_discovery_api_unavailable.db"
    engine, session_maker = _prepare_test_db(db_path)
    user = _seed_user(session_maker=session_maker, email="discovery-user@example.com")
    manager = _DiscoveryApiSearchManagerStub(loaded=False)

    async def override_db_session() -> AsyncGenerator[AsyncSession]:
        async with session_maker() as session:
            yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr("sift.services.discovery_service.get_plugin_manager", lambda: manager)
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)

    async def _resolve_feed_endpoint_stub(
        self: object,
        *,
        client: object,
        candidate: SearchFeedCandidate,
    ) -> str:
        del self, client
        return candidate.url

    monkeypatch.setattr(
        "sift.services.discovery_service.DiscoveryService._resolve_feed_endpoint_for_candidate",
        _resolve_feed_endpoint_stub,
    )

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/discovery/streams",
                json={"name": "Threat intel", "include_keywords": ["threat"]},
            )
            assert create_response.status_code == 201
            stream_id = create_response.json()["id"]

            copy_missing_response = client.post(
                "/api/v1/discovery/streams/copy-from-monitoring",
                json={"monitoring_stream_id": str(uuid4())},
            )
            assert copy_missing_response.status_code == 404

            generate_response = client.post(f"/api/v1/discovery/streams/{stream_id}/generate", json={})
            assert generate_response.status_code == 503
            assert generate_response.json()["detail"] == "Search provider plugin unavailable"
    finally:
        import asyncio

        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
        if db_path.exists():
            db_path.unlink()
