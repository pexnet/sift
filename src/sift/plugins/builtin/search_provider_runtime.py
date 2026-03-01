import os
import re
from typing import Any

import httpx

from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult

_ENV_REF_PATTERN = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")
_DEFAULT_TIMEOUT_SECONDS = 4.0


class SearchProviderRuntimePlugin:
    name = "search_provider_runtime"

    async def search_feeds(self, request: SearchFeedsRequest) -> SearchFeedsResult | None:
        provider = request.provider_chain[0] if request.provider_chain else ""
        if provider == "searxng":
            return await self._search_searxng(request)
        if provider == "brave_search":
            return await self._search_brave(request)
        if provider in {"google_custom_search", "duckduckgo_instant_answer"}:
            return SearchFeedsResult(
                provider=provider,
                candidates=[],
                warnings=["provider adapter is not enabled in this runtime"],
            )
        return SearchFeedsResult(provider=provider or "unconfigured", candidates=[], warnings=["unknown provider id"])

    async def _search_searxng(self, request: SearchFeedsRequest) -> SearchFeedsResult:
        base_url = str(request.provider_settings.get("base_url") or "http://localhost:8080/search")
        params: dict[str, str | int] = {
            "q": request.query,
            "format": "json",
            "language": "en-US",
            "safesearch": 0,
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(base_url, params=params, headers={"User-Agent": "sift-search-provider/1.0"})
        response.raise_for_status()
        payload = response.json()

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return SearchFeedsResult(provider="searxng", candidates=[], warnings=["invalid provider response payload"])

        candidates: list[SearchFeedCandidate] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = _as_non_empty_str(item.get("url"))
            title = _as_non_empty_str(item.get("title"))
            if url is None or title is None:
                continue
            candidates.append(
                SearchFeedCandidate(
                    title=title,
                    url=url,
                    site_url=_as_non_empty_str(item.get("parsed_url")) or _as_non_empty_str(item.get("engine")),
                    description=_as_non_empty_str(item.get("content")),
                    provider="searxng",
                )
            )
            if len(candidates) >= request.max_results:
                break
        return SearchFeedsResult(provider="searxng", candidates=candidates, warnings=[])

    async def _search_brave(self, request: SearchFeedsRequest) -> SearchFeedsResult:
        raw_api_key = request.provider_settings.get("api_key")
        api_key = _resolve_secret(raw_api_key)
        if not api_key:
            raise RuntimeError("missing brave_search api_key (expected env-ref or plaintext setting)")

        endpoint = str(request.provider_settings.get("endpoint") or "https://api.search.brave.com/res/v1/web/search")
        params: dict[str, str | int] = {"q": request.query, "count": request.max_results}
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": "sift-search-provider/1.0",
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

        web = payload.get("web")
        if not isinstance(web, dict):
            return SearchFeedsResult(provider="brave_search", candidates=[], warnings=["missing web results block"])
        raw_results = web.get("results")
        if not isinstance(raw_results, list):
            return SearchFeedsResult(provider="brave_search", candidates=[], warnings=["invalid web results payload"])

        candidates: list[SearchFeedCandidate] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = _as_non_empty_str(item.get("url"))
            title = _as_non_empty_str(item.get("title"))
            if url is None or title is None:
                continue
            candidates.append(
                SearchFeedCandidate(
                    title=title,
                    url=url,
                    site_url=_as_non_empty_str(item.get("profile", {}).get("url") if isinstance(item.get("profile"), dict) else None),
                    description=_as_non_empty_str(item.get("description")),
                    provider="brave_search",
                )
            )
            if len(candidates) >= request.max_results:
                break
        return SearchFeedsResult(provider="brave_search", candidates=candidates, warnings=[])


def _as_non_empty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _resolve_secret(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        match = _ENV_REF_PATTERN.match(normalized)
        if match:
            return os.getenv(match.group(1))
        return normalized or None
    return None
