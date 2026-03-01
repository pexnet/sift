from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult
from sift.services.search_service import SearchProviderBudget, SearchProviderService


class _SearchManagerStub:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def search_feeds(self, *, plugin_name: str, request: SearchFeedsRequest) -> SearchFeedsResult | None:
        del plugin_name
        provider = request.provider_chain[0]
        self.calls.append(provider)
        if provider == "searxng":
            return SearchFeedsResult(provider=provider, candidates=[], warnings=[])
        return SearchFeedsResult(
            provider=provider,
            candidates=[
                SearchFeedCandidate(
                    title="candidate",
                    url="https://example.com/feed.xml",
                    site_url="https://example.com",
                    description=None,
                    provider=provider,
                )
            ],
            warnings=[],
        )


async def _prepare_session_maker(tmp_path: Path, filename: str) -> tuple[AsyncEngine, async_sessionmaker]:
    db_path = tmp_path / filename
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, session_maker


@pytest.mark.asyncio
async def test_search_service_falls_back_to_next_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    service = SearchProviderService()
    engine, session_maker = await _prepare_session_maker(tmp_path, "search_service_fallback.db")

    try:
        async with session_maker() as session:
            result = await service.search_with_fallback(
                plugin_name="search_provider",
                session=session,
                query="ai",
                max_results=10,
                provider_chain=["searxng", "brave_search"],
                provider_budgets={
                    "searxng": SearchProviderBudget(10, 100, 1, 5, 25),
                    "brave_search": SearchProviderBudget(10, 100, 1, 5, 25),
                },
                provider_settings={},
                metadata={},
            )
    finally:
        await engine.dispose()

    assert result is not None
    assert result.provider == "brave_search"
    assert len(result.candidates) == 1
    assert manager.calls == ["searxng", "brave_search"]


@pytest.mark.asyncio
async def test_search_service_enforces_min_interval_budget(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    service = SearchProviderService()
    budgets = {"searxng": SearchProviderBudget(10, 100, 60_000, 5, 25)}
    engine, session_maker = await _prepare_session_maker(tmp_path, "search_service_min_interval.db")

    try:
        async with session_maker() as session:
            first = await service.search_with_fallback(
                plugin_name="search_provider",
                session=session,
                query="ai",
                max_results=10,
                provider_chain=["searxng"],
                provider_budgets=budgets,
                provider_settings={},
                metadata={},
            )
        async with session_maker() as session:
            second = await service.search_with_fallback(
                plugin_name="search_provider",
                session=session,
                query="ml",
                max_results=10,
                provider_chain=["searxng"],
                provider_budgets=budgets,
                provider_settings={},
                metadata={},
            )
    finally:
        await engine.dispose()

    assert first is not None
    assert second is not None
    assert second.candidates == []
    assert any("min_interval_ms not satisfied" in warning for warning in second.warnings)
    assert any(item.code == "min_interval_ms_not_satisfied" for item in second.warning_details)
    assert manager.calls == ["searxng"]


@pytest.mark.asyncio
async def test_search_service_enforces_max_requests_per_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    service = SearchProviderService()
    budgets = {"searxng": SearchProviderBudget(1, 100, 1, 5, 25)}
    engine, session_maker = await _prepare_session_maker(tmp_path, "search_service_per_run.db")

    try:
        async with session_maker() as session:
            result = await service.search_with_fallback(
                plugin_name="search_provider",
                session=session,
                query="ai",
                max_results=10,
                provider_chain=["searxng", "searxng"],
                provider_budgets=budgets,
                provider_settings={},
                metadata={},
            )
    finally:
        await engine.dispose()

    assert result is not None
    assert result.candidates == []
    assert any("max_requests_per_run exhausted" in warning for warning in result.warnings)
    assert manager.calls == ["searxng"]


@pytest.mark.asyncio
async def test_search_service_enforces_daily_budget_across_service_instances(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    engine, session_maker = await _prepare_session_maker(tmp_path, "search_service_daily_budget.db")
    budgets = {"brave_search": SearchProviderBudget(10, 1, 1, 5, 25)}

    first_service = SearchProviderService()
    second_service = SearchProviderService()

    try:
        async with session_maker() as session:
            first = await first_service.search_with_fallback(
                plugin_name="search_provider",
                session=session,
                query="first",
                max_results=10,
                provider_chain=["brave_search"],
                provider_budgets=budgets,
                provider_settings={},
                metadata={},
            )
        async with session_maker() as session:
            second = await second_service.search_with_fallback(
                plugin_name="search_provider",
                session=session,
                query="second",
                max_results=10,
                provider_chain=["brave_search"],
                provider_budgets=budgets,
                provider_settings={},
                metadata={},
            )
    finally:
        await engine.dispose()

    assert first is not None
    assert len(first.candidates) == 1
    assert second is not None
    assert second.candidates == []
    assert any("max_requests_per_day exhausted" in warning for warning in second.warnings)
    assert any(item.code == "max_requests_per_day_exhausted" for item in second.warning_details)
