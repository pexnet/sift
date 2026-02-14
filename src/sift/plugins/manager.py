from importlib import import_module

from sift.plugins.base import ArticleContext, ArticlePlugin


def _load_plugin(path: str) -> ArticlePlugin:
    module_path, class_name = path.split(":", maxsplit=1)
    module = import_module(module_path)
    plugin_class = getattr(module, class_name)
    plugin: ArticlePlugin = plugin_class()
    return plugin


class PluginManager:
    def __init__(self) -> None:
        self._plugins: list[ArticlePlugin] = []

    def load_from_paths(self, plugin_paths: list[str]) -> None:
        for path in plugin_paths:
            self._plugins.append(_load_plugin(path))

    def names(self) -> list[str]:
        return [plugin.name for plugin in self._plugins]

    async def run_ingested_hooks(self, article: ArticleContext) -> ArticleContext:
        current = article
        for plugin in self._plugins:
            current = await plugin.on_article_ingested(current)
        return current

