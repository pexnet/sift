from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ArticleContext:
    article_id: str
    title: str
    content_text: str
    metadata: Mapping[str, str]


class ArticlePlugin(Protocol):
    name: str

    async def on_article_ingested(self, article: ArticleContext) -> ArticleContext:
        """Enrich or transform article content after ingestion."""


@dataclass(slots=True)
class StreamClassifierContext:
    stream_id: str
    stream_name: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    source_contains: str | None
    language_equals: str | None
    classifier_config: Mapping[str, Any]
    metadata: Mapping[str, str]


@dataclass(slots=True)
class StreamClassificationDecision:
    matched: bool
    confidence: float
    reason: str = ""
    provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    findings: list[dict[str, Any]] | None = None


class StreamClassifierPlugin(Protocol):
    name: str

    async def classify_stream(
        self,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision | None:
        """Return optional classification decision for article/stream relevance."""


@dataclass(slots=True)
class SearchFeedsRequest:
    query: str
    provider_chain: list[str]
    max_results: int
    metadata: Mapping[str, str]


@dataclass(slots=True)
class SearchFeedCandidate:
    title: str
    url: str
    site_url: str | None
    description: str | None
    provider: str


@dataclass(slots=True)
class SearchFeedsResult:
    provider: str
    candidates: list[SearchFeedCandidate]
    warnings: list[str]


class SearchProviderPlugin(Protocol):
    name: str

    async def search_feeds(self, request: SearchFeedsRequest) -> SearchFeedsResult | None:
        """Return optional ephemeral feed/blog candidates for a search request."""
