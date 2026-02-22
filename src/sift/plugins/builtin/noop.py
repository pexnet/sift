from sift.plugins.base import ArticleContext


class NoopPlugin:
    name = "noop"

    async def on_article_ingested(self, article: ArticleContext) -> ArticleContext:
        return article
