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
