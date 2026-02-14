from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


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
    metadata: Mapping[str, str]


@dataclass(slots=True)
class StreamClassificationDecision:
    matched: bool
    confidence: float
    reason: str = ""


class StreamClassifierPlugin(Protocol):
    name: str

    async def classify_stream(
        self,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision | None:
        """Return optional classification decision for article/stream relevance."""

