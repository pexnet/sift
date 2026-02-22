from dataclasses import dataclass
from importlib import import_module
from typing import Any

from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext
from sift.plugins.registry import PluginRegistryEntry


@dataclass(slots=True)
class LoadedPlugin:
    id: str
    capabilities: frozenset[str]
    implementation: Any


def _load_plugin(path: str) -> Any:
    try:
        module_path, class_name = path.split(":", maxsplit=1)
    except ValueError as exc:
        raise ValueError(f"Invalid plugin class path '{path}'. Expected 'module.path:ClassName'.") from exc

    module = import_module(module_path)
    try:
        plugin_class = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(f"Plugin class '{class_name}' not found in module '{module_path}'.") from exc

    plugin: Any = plugin_class()
    return plugin


class PluginManager:
    def __init__(self) -> None:
        self._plugins: list[LoadedPlugin] = []

    def load_from_registry(self, plugins: list[PluginRegistryEntry]) -> None:
        self._plugins = []
        for entry in plugins:
            if not entry.enabled:
                continue
            implementation = _load_plugin(entry.backend.class_path)
            self._plugins.append(
                LoadedPlugin(
                    id=entry.id,
                    capabilities=frozenset(entry.capabilities),
                    implementation=implementation,
                )
            )

    def names(self) -> list[str]:
        return [plugin.id for plugin in self._plugins]

    async def run_ingested_hooks(self, article: ArticleContext) -> ArticleContext:
        current = article
        for plugin in self._plugins:
            if "ingest_hook" not in plugin.capabilities:
                continue
            on_article_ingested = getattr(plugin.implementation, "on_article_ingested", None)
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
            if plugin.id != plugin_name:
                continue
            if "stream_classifier" not in plugin.capabilities:
                return None
            classify_stream = getattr(plugin.implementation, "classify_stream", None)
            if callable(classify_stream):
                return await classify_stream(article, stream)
            return None
        return None

