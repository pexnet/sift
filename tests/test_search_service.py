import pytest

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


@pytest.mark.asyncio
async def test_search_service_falls_back_to_next_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    service = SearchProviderService()

    result = await service.search_with_fallback(
        plugin_name="search_provider",
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

    assert result is not None
    assert result.provider == "brave_search"
    assert len(result.candidates) == 1
    assert manager.calls == ["searxng", "brave_search"]


@pytest.mark.asyncio
async def test_search_service_enforces_min_interval_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    service = SearchProviderService()
    budgets = {"searxng": SearchProviderBudget(10, 100, 60_000, 5, 25)}

    first = await service.search_with_fallback(
        plugin_name="search_provider",
        query="ai",
        max_results=10,
        provider_chain=["searxng"],
        provider_budgets=budgets,
        provider_settings={},
        metadata={},
    )
    second = await service.search_with_fallback(
        plugin_name="search_provider",
        query="ml",
        max_results=10,
        provider_chain=["searxng"],
        provider_budgets=budgets,
        provider_settings={},
        metadata={},
    )

    assert first is not None
    assert second is not None
    assert second.candidates == []
    assert any("min_interval_ms not satisfied" in warning for warning in second.warnings)
    assert manager.calls == ["searxng"]


@pytest.mark.asyncio
async def test_search_service_enforces_max_requests_per_run(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _SearchManagerStub()
    monkeypatch.setattr("sift.services.search_service.get_plugin_manager", lambda: manager)
    service = SearchProviderService()
    budgets = {"searxng": SearchProviderBudget(1, 100, 1, 5, 25)}

    result = await service.search_with_fallback(
        plugin_name="search_provider",
        query="ai",
        max_results=10,
        provider_chain=["searxng", "searxng"],
        provider_budgets=budgets,
        provider_settings={},
        metadata={},
    )

    assert result is not None
    assert result.candidates == []
    assert any("max_requests_per_run exhausted" in warning for warning in result.warnings)
    assert manager.calls == ["searxng"]
