from importlib import import_module
from typing import Any

from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext


def _load_plugin(path: str) -> Any:
    module_path, class_name = path.split(":", maxsplit=1)
    module = import_module(module_path)
    plugin_class = getattr(module, class_name)
    plugin: Any = plugin_class()
    return plugin


class PluginManager:
    def __init__(self) -> None:
        self._plugins: list[Any] = []

    def load_from_paths(self, plugin_paths: list[str]) -> None:
        for path in plugin_paths:
            self._plugins.append(_load_plugin(path))

    def names(self) -> list[str]:
        return [str(getattr(plugin, "name", plugin.__class__.__name__)) for plugin in self._plugins]

    async def run_ingested_hooks(self, article: ArticleContext) -> ArticleContext:
        current = article
        for plugin in self._plugins:
            on_article_ingested = getattr(plugin, "on_article_ingested", None)
            if callable(on_article_ingested):
                current = await on_article_ingested(current)
        return current

    async def classify_stream(
        self,
        *,
        plugin_name: str,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision | None:
        for plugin in self._plugins:
            if str(getattr(plugin, "name", "")) != plugin_name:
                continue
            classify_stream = getattr(plugin, "classify_stream", None)
            if callable(classify_stream):
                return await classify_stream(article, stream)
            return None
        return None

