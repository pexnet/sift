from sift.plugins.base import SearchFeedsRequest, SearchFeedsResult


class SearchProviderNoopPlugin:
    name = "search_provider_noop"

    async def search_feeds(self, request: SearchFeedsRequest) -> SearchFeedsResult:
        provider = request.provider_chain[0] if request.provider_chain else "unconfigured"
        return SearchFeedsResult(
            provider=provider,
            candidates=[],
            warnings=["search provider runtime is configured but no external adapter is active in this baseline"],
        )
