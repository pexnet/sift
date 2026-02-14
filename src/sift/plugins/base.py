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

