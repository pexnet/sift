from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Feed, FeedRecommendation, KeywordStream, User
from sift.domain.schemas import DiscoveryStreamCreate
from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult
from sift.plugins.manager import PluginStatusSnapshot
from sift.plugins.registry import PluginBackendConfig, PluginRegistryEntry
from sift.services.discovery_service import (
    DiscoveryMonitoringStreamNotFoundError,
    DiscoveryRecommendationValidationError,
    DiscoveryStreamValidationError,
    discovery_service,
)


class _DiscoverySearchManagerStub:
    def __init__(self) -> None:
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
                loaded=True,
                capabilities=["search_provider"],
                startup_validation_status="ok",
                last_error=None,
                unavailable_reason=None,
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
                    url="https://example.com/feed.xml#section",
                    site_url="https://example.com#home",
                    description="test candidate",
                    provider="searxng",
                )
            ],
            warnings=[],
        )


@pytest.mark.asyncio
async def test_discovery_stream_create_requires_positive_criteria() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-empty@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(DiscoveryStreamValidationError):
            await discovery_service.create_stream(
                session=session,
                user_id=user.id,
                payload=DiscoveryStreamCreate(name="empty"),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_discovery_stream_generate_caps_query_variants_and_dedupes_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _DiscoverySearchManagerStub()
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

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-generate@example.com")
        session.add(user)
        await session.flush()

        stream = await discovery_service.create_stream(
            session=session,
            user_id=user.id,
            payload=DiscoveryStreamCreate(
                name="Threat intel",
                include_keywords=["threat", "intel", "research"],
                exclude_keywords=["jobs"],
            ),
        )

        result = await discovery_service.generate_for_stream(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            max_results_per_query=10,
            max_candidates=20,
        )

    await engine.dispose()

    assert len(result.query_variants) == 2
    assert len(manager.calls) == 2
    assert manager.calls[0].endswith("-jobs")
    assert len(result.candidates) == 1
    assert result.candidates[0].url == "https://example.com/feed.xml"
    assert result.candidates[0].site_url == "https://example.com"
    assert result.persisted_count == 1
    assert result.pending_count == 1
    assert result.resolved_existing_count == 0


@pytest.mark.asyncio
async def test_discovery_generation_marks_existing_user_feed_as_resolved_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _DiscoverySearchManagerStub()
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

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-existing@example.com")
        session.add(user)
        await session.flush()
        session.add(Feed(owner_id=user.id, title="Existing feed", url="https://example.com/feed.xml"))
        await session.commit()

        stream = await discovery_service.create_stream(
            session=session,
            user_id=user.id,
            payload=DiscoveryStreamCreate(name="Threat intel", include_keywords=["threat"]),
        )
        result = await discovery_service.generate_for_stream(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            max_results_per_query=10,
            max_candidates=20,
        )

        recommendations, total, _ = await discovery_service.list_recommendations(
            session=session,
            user_id=user.id,
            status_filter=None,
            q=None,
            sort_by="updated_at",
            sort_direction="desc",
            limit=20,
            offset=0,
        )

    await engine.dispose()

    assert result.persisted_count == 1
    assert result.pending_count == 0
    assert result.resolved_existing_count == 1
    assert total == 1
    assert recommendations[0].status == "resolved_existing"


@pytest.mark.asyncio
async def test_discovery_recommendation_transition_rules_and_list_sorting() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-transitions@example.com")
        session.add(user)
        await session.flush()

        older = FeedRecommendation(
            user_id=user.id,
            status="pending",
            feed_url="https://alpha.example.com/feed.xml",
            feed_url_normalized="https://alpha.example.com/feed.xml",
            feed_title="Alpha Feed",
            site_url="https://alpha.example.com",
            provider="searxng",
            created_at=datetime.now(UTC) - timedelta(days=2),
            updated_at=datetime.now(UTC) - timedelta(days=2),
            last_seen_at=datetime.now(UTC) - timedelta(days=2),
        )
        newer = FeedRecommendation(
            user_id=user.id,
            status="pending",
            feed_url="https://zeta.example.com/feed.xml",
            feed_url_normalized="https://zeta.example.com/feed.xml",
            feed_title="Zeta Feed",
            site_url="https://zeta.example.com",
            provider="searxng",
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            last_seen_at=datetime.now(UTC) - timedelta(days=1),
        )
        session.add_all([older, newer])
        await session.commit()

        denied = await discovery_service.decide_recommendation(
            session=session,
            user_id=user.id,
            recommendation_id=older.id,
            decision="deny",
        )
        assert denied.status == "denied"

        with pytest.raises(DiscoveryRecommendationValidationError):
            await discovery_service.decide_recommendation(
                session=session,
                user_id=user.id,
                recommendation_id=older.id,
                decision="deny",
            )

        with pytest.raises(DiscoveryRecommendationValidationError):
            await discovery_service.decide_recommendation(
                session=session,
                user_id=user.id,
                recommendation_id=older.id,
                decision="accept",
            )

        reset = await discovery_service.reset_recommendation(
            session=session,
            user_id=user.id,
            recommendation_id=older.id,
        )
        assert reset.status == "pending"

        rows, total, _ = await discovery_service.list_recommendations(
            session=session,
            user_id=user.id,
            status_filter="pending",
            q="zeta",
            sort_by="feed_title",
            sort_direction="asc",
            limit=20,
            offset=0,
        )
        assert total == 1
        assert len(rows) == 1
        assert rows[0].feed_title == "Zeta Feed"

    await engine.dispose()


@pytest.mark.asyncio
async def test_copy_discovery_stream_from_monitoring() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-copy@example.com")
        session.add(user)
        await session.flush()
        monitoring_stream = KeywordStream(
            user_id=user.id,
            name="Threat watch",
            description="monitoring description",
            is_active=True,
            priority=120,
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
        session.add(monitoring_stream)
        await session.commit()

        copied = await discovery_service.copy_stream_from_monitoring(
            session=session,
            user_id=user.id,
            monitoring_stream_id=monitoring_stream.id,
            name=None,
        )

        assert copied.name == "Threat watch (discovery)"
        assert copied.description == "monitoring description"
        assert copied.match_query == "threat AND intel"
        assert copied.priority == 120
        assert copied.is_active is True
        assert copied.include_keywords_json == '["threat", "intel"]'
        assert copied.exclude_keywords_json == '["jobs"]'

    await engine.dispose()


@pytest.mark.asyncio
async def test_copy_discovery_stream_from_monitoring_not_found() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-copy-missing@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(DiscoveryMonitoringStreamNotFoundError):
            await discovery_service.copy_stream_from_monitoring(
                session=session,
                user_id=user.id,
                monitoring_stream_id=user.id,
                name=None,
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_copy_discovery_stream_from_monitoring_rejects_non_copyable_criteria() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="discovery-copy-invalid@example.com")
        session.add(user)
        await session.flush()
        monitoring_stream = KeywordStream(
            user_id=user.id,
            name="Regex only",
            description=None,
            is_active=True,
            priority=100,
            match_query=None,
            include_keywords_json="[]",
            exclude_keywords_json="[]",
            include_regex_json='["threat.*"]',
            exclude_regex_json="[]",
            source_contains=None,
            language_equals=None,
            classifier_mode="rules_only",
            classifier_plugin=None,
            classifier_config_json="{}",
            classifier_min_confidence=0.7,
        )
        session.add(monitoring_stream)
        await session.commit()

        with pytest.raises(DiscoveryStreamValidationError):
            await discovery_service.copy_stream_from_monitoring(
                session=session,
                user_id=user.id,
                monitoring_stream_id=monitoring_stream.id,
                name=None,
            )

    await engine.dispose()
