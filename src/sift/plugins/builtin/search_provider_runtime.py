import os
import re
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest, SearchFeedsResult

_ENV_REF_PATTERN = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")
_DEFAULT_TIMEOUT_SECONDS = 4.0
_SUPPORTED_SCHEMES = frozenset({"http", "https"})


def _warn(code: str, message: str) -> str:
    return f"{code}: {message}"


class SearchProviderRuntimePlugin:
    name = "search_provider_runtime"

    async def search_feeds(self, request: SearchFeedsRequest) -> SearchFeedsResult | None:
        provider = request.provider_chain[0] if request.provider_chain else ""
        if not request.query.strip():
            return SearchFeedsResult(provider=provider or "unconfigured", candidates=[], warnings=[_warn("invalid_query", "query is empty")])
        if provider == "searxng":
            return await self._search_searxng(request)
        if provider == "brave_search":
            return await self._search_brave(request)
        if provider in {"google_custom_search", "duckduckgo_instant_answer"}:
            return SearchFeedsResult(
                provider=provider,
                candidates=[],
                warnings=[_warn("provider_not_enabled", "provider adapter is not enabled in this runtime")],
            )
        return SearchFeedsResult(
            provider=provider or "unconfigured",
            candidates=[],
            warnings=[_warn("unknown_provider_id", "unknown provider id")],
        )

    async def _search_searxng(self, request: SearchFeedsRequest) -> SearchFeedsResult:
        base_url = str(request.provider_settings.get("base_url") or "http://localhost:8080/search")
        params: dict[str, str | int] = {
            "q": request.query,
            "format": "json",
            "language": "en-US",
            "safesearch": 0,
        }
        payload, warnings = await self._fetch_json_payload(
            provider="searxng",
            endpoint=base_url,
            params=params,
            headers={"User-Agent": "sift-search-provider/1.0"},
        )
        if warnings:
            return SearchFeedsResult(provider="searxng", candidates=[], warnings=warnings)
        if not isinstance(payload, dict):
            return SearchFeedsResult(
                provider="searxng",
                candidates=[],
                warnings=[_warn("invalid_response_payload", "provider response root must be a JSON object")],
            )

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return SearchFeedsResult(
                provider="searxng",
                candidates=[],
                warnings=[_warn("invalid_response_payload", "provider response payload must include a results list")],
            )

        candidates: list[SearchFeedCandidate] = []
        seen_urls: set[str] = set()
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = _normalize_url(item.get("url"))
            title = _as_non_empty_str(item.get("title"))
            if url is None or title is None:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(
                SearchFeedCandidate(
                    title=title,
                    url=url,
                    site_url=_extract_searxng_site_url(item) or _origin_from_url(url),
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
            return SearchFeedsResult(
                provider="brave_search",
                candidates=[],
                warnings=[_warn("missing_api_key", "missing brave_search api_key (expected env-ref or plaintext setting)")],
            )

        endpoint = str(request.provider_settings.get("endpoint") or "https://api.search.brave.com/res/v1/web/search")
        params: dict[str, str | int] = {"q": request.query, "count": request.max_results}
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": "sift-search-provider/1.0",
        }
        payload, warnings = await self._fetch_json_payload(
            provider="brave_search",
            endpoint=endpoint,
            params=params,
            headers=headers,
        )
        if warnings:
            return SearchFeedsResult(provider="brave_search", candidates=[], warnings=warnings)
        if not isinstance(payload, dict):
            return SearchFeedsResult(
                provider="brave_search",
                candidates=[],
                warnings=[_warn("invalid_response_payload", "provider response root must be a JSON object")],
            )

        web = payload.get("web")
        if not isinstance(web, dict):
            return SearchFeedsResult(
                provider="brave_search",
                candidates=[],
                warnings=[_warn("invalid_response_payload", "provider response missing web results block")],
            )
        raw_results = web.get("results")
        if not isinstance(raw_results, list):
            return SearchFeedsResult(
                provider="brave_search",
                candidates=[],
                warnings=[_warn("invalid_response_payload", "provider response has invalid web results payload")],
            )

        candidates: list[SearchFeedCandidate] = []
        seen_urls: set[str] = set()
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = _normalize_url(item.get("url"))
            title = _as_non_empty_str(item.get("title"))
            if url is None or title is None:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            profile = item.get("profile")
            profile_url = profile.get("url") if isinstance(profile, dict) else None
            candidates.append(
                SearchFeedCandidate(
                    title=title,
                    url=url,
                    site_url=_normalize_url(profile_url) or _origin_from_url(url),
                    description=_as_non_empty_str(item.get("description")),
                    provider="brave_search",
                )
            )
            if len(candidates) >= request.max_results:
                break
        return SearchFeedsResult(provider="brave_search", candidates=candidates, warnings=[])

    async def _fetch_json_payload(
        self,
        *,
        provider: str,
        endpoint: str,
        params: dict[str, str | int],
        headers: dict[str, str],
    ) -> tuple[dict[str, Any] | list[Any] | None, list[str]]:
        request: httpx.Request | None = None
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS, follow_redirects=True) as client:
                response = await client.get(endpoint, params=params, headers=headers)
                request = response.request
            status_code = response.status_code
            if status_code >= 400:
                if status_code == 429:
                    return None, [_warn("http_status_429", f"{provider} returned HTTP {status_code}")]
                if status_code >= 500:
                    return None, [_warn("http_status_5xx", f"{provider} returned HTTP {status_code}")]
                return None, [_warn("http_status_4xx", f"{provider} returned HTTP {status_code}")]
            try:
                payload = response.json()
            except ValueError:
                return None, [_warn("invalid_json", f"{provider} returned invalid JSON payload")]
            if not isinstance(payload, (dict, list)):
                return None, [_warn("invalid_response_payload", f"{provider} response payload must be JSON object or list")]
            return payload, []
        except httpx.TimeoutException:
            return None, [_warn("timeout", f"{provider} request timed out")]
        except httpx.RequestError as exc:
            url = str(request.url) if request is not None else endpoint
            return None, [_warn("network_error", f"{provider} request failed for {url} ({type(exc).__name__})")]


def _as_non_empty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _normalize_url(value: Any) -> str | None:
    raw = _as_non_empty_str(value)
    if raw is None:
        return None
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in _SUPPORTED_SCHEMES:
        return None
    if not parsed.netloc:
        return None
    normalized = parsed._replace(fragment="")
    return urlunparse(normalized)


def _origin_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _SUPPORTED_SCHEMES or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _extract_searxng_site_url(item: dict[str, Any]) -> str | None:
    parsed_url = item.get("parsed_url")
    if isinstance(parsed_url, (list, tuple)) and len(parsed_url) >= 2:
        scheme = _as_non_empty_str(parsed_url[0])
        netloc = _as_non_empty_str(parsed_url[1])
        if scheme and netloc and scheme.lower() in _SUPPORTED_SCHEMES:
            return f"{scheme}://{netloc}"
    normalized = _normalize_url(parsed_url)
    if normalized is not None:
        return _origin_from_url(normalized) or normalized
    return None


def _resolve_secret(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        match = _ENV_REF_PATTERN.match(normalized)
        if match:
            return os.getenv(match.group(1))
        return normalized or None
    return None
