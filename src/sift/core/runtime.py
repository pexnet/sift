from functools import lru_cache

from sift.config import get_settings
from sift.plugins.manager import PluginManager
from sift.plugins.registry import load_plugin_registry


@lru_cache
def get_plugin_manager() -> PluginManager:
    settings = get_settings()
    manager = PluginManager(
        timeout_ingest_ms=settings.plugin_timeout_ingest_ms,
        timeout_classifier_ms=settings.plugin_timeout_classifier_ms,
        timeout_discovery_ms=settings.plugin_timeout_discovery_ms,
        timeout_summary_ms=settings.plugin_timeout_summary_ms,
        diagnostics_enabled=settings.plugin_diagnostics_enabled,
    )
    registry = load_plugin_registry(settings.plugin_registry_path)
    manager.load_from_registry(registry.plugins)
    return manager
