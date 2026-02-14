from functools import lru_cache

from sift.config import get_settings
from sift.plugins.manager import PluginManager


@lru_cache
def get_plugin_manager() -> PluginManager:
    settings = get_settings()
    manager = PluginManager()
    manager.load_from_paths(settings.plugin_paths)
    return manager

