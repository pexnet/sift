from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

import sift.plugins.builtin.search_provider_runtime as runtime_module
from sift.plugins.base import SearchFeedsRequest

ResponseHandler = Callable[[str, dict[str, str | int], dict[str, str]], httpx.Response | Awaitable[httpx.Response]]


def _request(*, provider: str, provider_settings: dict[str, Any] | None = None) -> SearchFeedsRequest:
    return SearchFeedsRequest(
        query="ai feeds",
        provider_chain=[provider],
        max_results=10,
        provider_settings=provider_settings or {},
        metadata={},
    )


def _install_async_client_stub(monkeypatch: pytest.MonkeyPatch, handler: ResponseHandler) -> None:
    class _AsyncClientStub:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        async def __aenter__(self) -> "_AsyncClientStub":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            del exc_type, exc, tb

        async def get(self, url: str, *, params: dict[str, str | int], headers: dict[str, str]) -> httpx.Response:
            response_or_awaitable = handler(url, params, headers)
            if isinstance(response_or_awaitable, httpx.Response):
                return response_or_awaitable
            return await response_or_awaitable

    monkeypatch.setattr(runtime_module.httpx, "AsyncClient", _AsyncClientStub)


@pytest.mark.asyncio
async def test_search_provider_runtime_returns_timeout_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, params: dict[str, str | int], headers: dict[str, str]) -> httpx.Response:
        del params, headers
        request = httpx.Request("GET", url)
        raise httpx.ReadTimeout("timeout", request=request)

    _install_async_client_stub(monkeypatch, handler)
    plugin = runtime_module.SearchProviderRuntimePlugin()

    result = await plugin.search_feeds(_request(provider="searxng"))

    assert result is not None
    assert result.provider == "searxng"
    assert result.candidates == []
    assert result.warnings == ["timeout: searxng request timed out"]


@pytest.mark.asyncio
async def test_search_provider_runtime_maps_http_429_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, params: dict[str, str | int], headers: dict[str, str]) -> httpx.Response:
        del params, headers
        request = httpx.Request("GET", url)
        return httpx.Response(status_code=429, request=request, json={"error": "rate_limited"})

    _install_async_client_stub(monkeypatch, handler)
    plugin = runtime_module.SearchProviderRuntimePlugin()

    result = await plugin.search_feeds(
        _request(provider="brave_search", provider_settings={"api_key": "test-api-key"})
    )

    assert result is not None
    assert result.provider == "brave_search"
    assert result.candidates == []
    assert result.warnings == ["http_status_429: brave_search returned HTTP 429"]


@pytest.mark.asyncio
async def test_search_provider_runtime_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, params: dict[str, str | int], headers: dict[str, str]) -> httpx.Response:
        del params, headers
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            request=request,
            content=b"{not-json",
            headers={"content-type": "application/json"},
        )

    _install_async_client_stub(monkeypatch, handler)
    plugin = runtime_module.SearchProviderRuntimePlugin()

    result = await plugin.search_feeds(_request(provider="searxng"))

    assert result is not None
    assert result.provider == "searxng"
    assert result.candidates == []
    assert result.warnings == ["invalid_json: searxng returned invalid JSON payload"]


@pytest.mark.asyncio
async def test_search_provider_runtime_dedupes_and_normalizes_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, params: dict[str, str | int], headers: dict[str, str]) -> httpx.Response:
        del params, headers
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            request=request,
            json={
                "results": [
                    {
                        "url": " https://example.com/feed.xml#fragment ",
                        "title": "Example feed",
                        "parsed_url": ["https", "example.com", "/feed.xml", "", "", ""],
                        "content": "first",
                    },
                    {
                        "url": "https://example.com/feed.xml",
                        "title": "Duplicate feed",
                        "parsed_url": ["https", "example.com", "/feed.xml", "", "", ""],
                        "content": "second",
                    },
                ]
            },
        )

    _install_async_client_stub(monkeypatch, handler)
    plugin = runtime_module.SearchProviderRuntimePlugin()

    result = await plugin.search_feeds(_request(provider="searxng"))

    assert result is not None
    assert len(result.candidates) == 1
    assert result.candidates[0].url == "https://example.com/feed.xml"
    assert result.candidates[0].site_url == "https://example.com"
    assert result.warnings == []


@pytest.mark.asyncio
async def test_search_provider_runtime_requires_brave_api_key() -> None:
    plugin = runtime_module.SearchProviderRuntimePlugin()

    result = await plugin.search_feeds(_request(provider="brave_search", provider_settings={}))

    assert result is not None
    assert result.provider == "brave_search"
    assert result.candidates == []
    assert result.warnings == [
        "missing_api_key: missing brave_search api_key (expected env-ref or plaintext setting)"
    ]
