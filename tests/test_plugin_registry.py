from pathlib import Path

import pytest

from sift.plugins.base import ArticleContext, StreamClassifierContext
from sift.plugins.manager import PluginManager
from sift.plugins.registry import PluginRegistryError, load_plugin_registry


def _write_registry(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_plugin_registry_valid_file(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: noop
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - ingest_hook
    settings: {}
  - id: keyword_heuristic_classifier
    enabled: true
    backend:
      class_path: sift.plugins.builtin.keyword_heuristic_classifier:KeywordHeuristicClassifierPlugin
    capabilities:
      - stream_classifier
    settings: {}
""".strip(),
    )

    registry = load_plugin_registry(str(registry_path))
    assert registry.version == 1
    assert [entry.id for entry in registry.plugins] == ["noop", "keyword_heuristic_classifier"]
    assert [entry.id for entry in registry.enabled_plugins()] == ["noop", "keyword_heuristic_classifier"]


def test_load_plugin_registry_rejects_unknown_capability(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: noop
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - unknown_capability
    settings: {}
""".strip(),
    )

    with pytest.raises(PluginRegistryError) as exc_info:
        load_plugin_registry(str(registry_path))
    assert "Unknown capability" in str(exc_info.value)


def test_load_plugin_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: noop
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - ingest_hook
    settings: {}
  - id: noop
    enabled: true
    backend:
      class_path: sift.plugins.builtin.keyword_heuristic_classifier:KeywordHeuristicClassifierPlugin
    capabilities:
      - stream_classifier
    settings: {}
""".strip(),
    )

    with pytest.raises(PluginRegistryError) as exc_info:
        load_plugin_registry(str(registry_path))
    assert "Duplicate plugin id 'noop'" in str(exc_info.value)


def test_load_plugin_registry_rejects_plaintext_sensitive_settings(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: discover_feeds
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - discover_feeds
    settings:
      discover_feeds:
        provider_budgets:
          searxng:
            max_requests_per_run: 10
            max_requests_per_day: 100
            min_interval_ms: 250
            max_query_variants_per_stream: 5
            max_results_per_query: 25
      api_key: plaintext-value
""".strip(),
    )

    with pytest.raises(PluginRegistryError) as exc_info:
        load_plugin_registry(str(registry_path))
    assert "sensitive values must reference env vars" in str(exc_info.value)
    assert "settings.api_key" in str(exc_info.value)


def test_load_plugin_registry_accepts_env_ref_sensitive_settings(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: discover_feeds
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - discover_feeds
    settings:
      discover_feeds:
        provider_chain:
          - searxng
        provider_budgets:
          searxng:
            max_requests_per_run: 10
            max_requests_per_day: 100
            min_interval_ms: 250
            max_query_variants_per_stream: 5
            max_results_per_query: 25
      api_key: "${DISCOVERY_API_KEY}"
""".strip(),
    )

    registry = load_plugin_registry(str(registry_path))
    assert [entry.id for entry in registry.plugins] == ["discover_feeds"]


def test_load_plugin_registry_rejects_discovery_budget_contract_violations(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: discover_feeds
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - discover_feeds
    settings:
      discover_feeds:
        provider_budgets:
          searxng:
            max_requests_per_run: 50
            max_requests_per_day: 10
            min_interval_ms: 0
            max_query_variants_per_stream: 0
            max_results_per_query: 25
""".strip(),
    )

    with pytest.raises(PluginRegistryError) as exc_info:
        load_plugin_registry(str(registry_path))
    error_message = str(exc_info.value)
    assert "settings.discover_feeds.provider_budgets.searxng.min_interval_ms: must be an integer >= 1" in error_message
    assert (
        "settings.discover_feeds.provider_budgets.searxng.max_query_variants_per_stream: must be an integer >= 1"
        in error_message
    )
    assert "settings.discover_feeds.provider_budgets.searxng.max_requests_per_day: must be >= max_requests_per_run" in (
        error_message
    )


def test_load_plugin_registry_accepts_valid_discovery_budget_contract(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: discover_feeds
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - discover_feeds
    settings:
      discover_feeds:
        provider_chain:
          - searxng
          - brave_search
        provider_budgets:
          searxng:
            max_requests_per_run: 10
            max_requests_per_day: 100
            min_interval_ms: 250
            max_query_variants_per_stream: 5
            max_results_per_query: 25
          brave_search:
            max_requests_per_run: 5
            max_requests_per_day: 25
            min_interval_ms: 400
            max_query_variants_per_stream: 4
            max_results_per_query: 10
""".strip(),
    )

    registry = load_plugin_registry(str(registry_path))
    discover_settings = registry.plugins[0].settings["discover_feeds"]
    assert isinstance(discover_settings, dict)
    assert discover_settings["provider_chain"] == ["searxng", "brave_search"]


@pytest.mark.asyncio
async def test_plugin_manager_dispatches_by_registry_capability(tmp_path: Path) -> None:
    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: noop
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - ingest_hook
    settings: {}
  - id: keyword_heuristic_classifier
    enabled: true
    backend:
      class_path: sift.plugins.builtin.keyword_heuristic_classifier:KeywordHeuristicClassifierPlugin
    capabilities:
      - stream_classifier
    settings: {}
""".strip(),
    )

    registry = load_plugin_registry(str(registry_path))
    manager = PluginManager()
    manager.load_from_registry(registry.plugins)

    article = ArticleContext(
        article_id="a1",
        title="Title",
        content_text="Content",
        metadata={"source_url": "https://example.com"},
    )
    processed = await manager.run_ingested_hooks(article)
    assert processed == article

    decision = await manager.classify_stream(
        plugin_name="keyword_heuristic_classifier",
        article=article,
        stream=StreamClassifierContext(
            stream_id="s1",
            stream_name="stream",
            include_keywords=[],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_config={},
            metadata={"source_url": "https://example.com", "language": "en"},
        ),
    )
    assert decision is not None
    assert decision.matched is True
    assert decision.provider == "builtin"

    missing_decision = await manager.classify_stream(
        plugin_name="noop",
        article=article,
        stream=StreamClassifierContext(
            stream_id="s1",
            stream_name="stream",
            include_keywords=[],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_config={},
            metadata={"source_url": "https://example.com", "language": "en"},
        ),
    )
    assert missing_decision is None


def test_runtime_get_plugin_manager_uses_registry_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sift.config import get_settings
    from sift.core.runtime import get_plugin_manager

    registry_path = _write_registry(
        tmp_path / "plugins.yaml",
        """
version: 1
plugins:
  - id: noop
    enabled: true
    backend:
      class_path: sift.plugins.builtin.noop:NoopPlugin
    capabilities:
      - ingest_hook
    settings: {}
""".strip(),
    )

    monkeypatch.setenv("SIFT_PLUGIN_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    get_plugin_manager.cache_clear()
    try:
        manager = get_plugin_manager()
        assert manager.names() == ["noop"]
    finally:
        get_plugin_manager.cache_clear()
        get_settings.cache_clear()
