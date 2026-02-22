import asyncio
import logging
from datetime import UTC, datetime

import pytest

import sift.plugins.manager as plugin_manager_module
from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext
from sift.plugins.manager import PluginManager
from sift.plugins.registry import PluginRegistryEntry
from sift.plugins.telemetry import PluginMetricSample


class _BrokenIngestPlugin:
    async def on_article_ingested(self, article: ArticleContext) -> ArticleContext:
        del article
        raise RuntimeError("ingest boom")


class _AppendTitleIngestPlugin:
    async def on_article_ingested(self, article: ArticleContext) -> ArticleContext:
        return ArticleContext(
            article_id=article.article_id,
            title=f"{article.title} [processed]",
            content_text=article.content_text,
            metadata=article.metadata,
        )


class _SlowClassifierPlugin:
    async def classify_stream(
        self,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision:
        del article
        del stream
        await asyncio.sleep(0.05)
        return StreamClassificationDecision(matched=True, confidence=1.0, reason="slow")


class _NoClassifierMethodPlugin:
    pass


def _entry(*, plugin_id: str, class_path: str, capabilities: list[str], enabled: bool = True) -> PluginRegistryEntry:
    return PluginRegistryEntry.model_validate(
        {
            "id": plugin_id,
            "enabled": enabled,
            "backend": {"class_path": class_path},
            "capabilities": capabilities,
            "settings": {},
        }
    )


def _sample_map(
    samples: list[PluginMetricSample],
    *,
    label_keys: tuple[str, ...],
) -> dict[tuple[str, ...], float]:
    mapped: dict[tuple[str, ...], float] = {}
    for sample in samples:
        key = tuple(sample.labels[key] for key in label_keys)
        mapped[key] = sample.value
    return mapped


@pytest.mark.asyncio
async def test_ingest_hook_failure_is_isolated_and_counters_update(monkeypatch: pytest.MonkeyPatch) -> None:
    plugins_by_path = {
        "test.plugins:broken": _BrokenIngestPlugin(),
        "test.plugins:append": _AppendTitleIngestPlugin(),
    }
    monkeypatch.setattr(plugin_manager_module, "_load_plugin", lambda path: plugins_by_path[path])

    manager = PluginManager(timeout_ingest_ms=250)
    manager.load_from_registry(
        [
            _entry(plugin_id="broken_ingest", class_path="test.plugins:broken", capabilities=["ingest_hook"]),
            _entry(plugin_id="append_ingest", class_path="test.plugins:append", capabilities=["ingest_hook"]),
        ]
    )

    article = ArticleContext(article_id="a1", title="hello", content_text="body", metadata={"k": "v"})
    processed = await manager.run_ingested_hooks(article)
    assert processed.title == "hello [processed]"

    snapshots = {item.plugin_id: item for item in manager.get_status_snapshots()}
    assert snapshots["broken_ingest"].runtime_counters["ingest_hook"]["failure_count"] == 1
    assert snapshots["append_ingest"].runtime_counters["ingest_hook"]["success_count"] == 1


@pytest.mark.asyncio
async def test_classifier_timeout_marks_timeout_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    plugins_by_path = {"test.plugins:slow": _SlowClassifierPlugin()}
    monkeypatch.setattr(plugin_manager_module, "_load_plugin", lambda path: plugins_by_path[path])

    manager = PluginManager(timeout_classifier_ms=1)
    manager.load_from_registry(
        [_entry(plugin_id="slow_classifier", class_path="test.plugins:slow", capabilities=["stream_classifier"])]
    )

    decision = await manager.classify_stream(
        plugin_name="slow_classifier",
        article=ArticleContext(article_id="a1", title="t", content_text="c", metadata={}),
        stream=StreamClassifierContext(
            stream_id="s1",
            stream_name="s",
            include_keywords=[],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_config={},
            metadata={},
        ),
    )
    assert decision is None

    snapshot = {item.plugin_id: item for item in manager.get_status_snapshots()}["slow_classifier"]
    assert snapshot.runtime_counters["stream_classifier"]["timeout_count"] == 1


@pytest.mark.asyncio
async def test_plugin_telemetry_metrics_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    plugins_by_path = {
        "test.plugins:broken": _BrokenIngestPlugin(),
        "test.plugins:append": _AppendTitleIngestPlugin(),
        "test.plugins:slow": _SlowClassifierPlugin(),
    }
    monkeypatch.setattr(plugin_manager_module, "_load_plugin", lambda path: plugins_by_path[path])

    manager = PluginManager(timeout_classifier_ms=1)
    manager.load_from_registry(
        [
            _entry(plugin_id="broken_ingest", class_path="test.plugins:broken", capabilities=["ingest_hook"]),
            _entry(plugin_id="append_ingest", class_path="test.plugins:append", capabilities=["ingest_hook"]),
            _entry(plugin_id="slow_classifier", class_path="test.plugins:slow", capabilities=["stream_classifier"]),
        ]
    )

    article = ArticleContext(article_id="a1", title="hello", content_text="body", metadata={"k": "v"})
    await manager.run_ingested_hooks(article)
    await manager.classify_stream(
        plugin_name="slow_classifier",
        article=article,
        stream=StreamClassifierContext(
            stream_id="s1",
            stream_name="s",
            include_keywords=[],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_config={},
            metadata={},
        ),
    )

    snapshot = manager.get_telemetry_snapshot()
    assert set(snapshot.keys()) == {
        "sift_plugin_invocations_total",
        "sift_plugin_invocation_duration_seconds",
        "sift_plugin_timeouts_total",
        "sift_plugin_dispatch_failures_total",
    }

    invocations = _sample_map(
        snapshot["sift_plugin_invocations_total"],
        label_keys=("plugin_id", "capability", "result"),
    )
    assert invocations[("broken_ingest", "ingest_hook", "failure")] == 1.0
    assert invocations[("append_ingest", "ingest_hook", "success")] == 1.0
    assert invocations[("slow_classifier", "stream_classifier", "timeout")] == 1.0

    durations = _sample_map(
        snapshot["sift_plugin_invocation_duration_seconds"],
        label_keys=("plugin_id", "capability", "result"),
    )
    assert durations[("broken_ingest", "ingest_hook", "failure")] >= 0.0
    assert durations[("append_ingest", "ingest_hook", "success")] >= 0.0
    assert durations[("slow_classifier", "stream_classifier", "timeout")] >= 0.0

    timeouts = _sample_map(
        snapshot["sift_plugin_timeouts_total"],
        label_keys=("plugin_id", "capability"),
    )
    assert timeouts[("slow_classifier", "stream_classifier")] == 1.0

    dispatch_failures = _sample_map(
        snapshot["sift_plugin_dispatch_failures_total"],
        label_keys=("capability",),
    )
    assert dispatch_failures[("ingest_hook",)] == 1.0
    assert dispatch_failures[("stream_classifier",)] == 1.0

    metrics_text = manager.render_telemetry_prometheus()
    assert "sift_plugin_invocations_total" in metrics_text
    assert "sift_plugin_invocation_duration_seconds" in metrics_text
    assert "sift_plugin_timeouts_total" in metrics_text
    assert "sift_plugin_dispatch_failures_total" in metrics_text


@pytest.mark.asyncio
async def test_plugin_dispatch_logging_contract(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    plugins_by_path = {
        "test.plugins:broken": _BrokenIngestPlugin(),
        "test.plugins:append": _AppendTitleIngestPlugin(),
    }
    monkeypatch.setattr(plugin_manager_module, "_load_plugin", lambda path: plugins_by_path[path])

    manager = PluginManager(timeout_ingest_ms=250)
    manager.load_from_registry(
        [
            _entry(plugin_id="broken_ingest", class_path="test.plugins:broken", capabilities=["ingest_hook"]),
            _entry(plugin_id="append_ingest", class_path="test.plugins:append", capabilities=["ingest_hook"]),
        ]
    )

    caplog.set_level(logging.INFO, logger="sift.plugins.manager")
    article = ArticleContext(article_id="a1", title="hello", content_text="body", metadata={"k": "v"})
    await manager.run_ingested_hooks(article)

    dispatch_events = {
        str(getattr(record, "event", "")): record
        for record in caplog.records
        if str(getattr(record, "event", "")).startswith("plugin.dispatch.")
    }

    assert "plugin.dispatch.start" in dispatch_events
    assert "plugin.dispatch.complete" in dispatch_events
    assert "plugin.dispatch.error" in dispatch_events

    start_record = dispatch_events["plugin.dispatch.start"]
    assert isinstance(getattr(start_record, "plugin_id", None), str)
    assert getattr(start_record, "capability", None) == "ingest_hook"
    assert getattr(start_record, "result", None) == "started"
    assert isinstance(getattr(start_record, "duration_ms", None), int)

    complete_record = dispatch_events["plugin.dispatch.complete"]
    assert isinstance(getattr(complete_record, "plugin_id", None), str)
    assert getattr(complete_record, "capability", None) == "ingest_hook"
    assert getattr(complete_record, "result", None) == "success"
    assert isinstance(getattr(complete_record, "duration_ms", None), int)

    error_record = dispatch_events["plugin.dispatch.error"]
    assert isinstance(getattr(error_record, "plugin_id", None), str)
    assert getattr(error_record, "capability", None) == "ingest_hook"
    assert getattr(error_record, "result", None) == "failure"
    assert isinstance(getattr(error_record, "duration_ms", None), int)
    assert isinstance(getattr(error_record, "error_type", None), str)


def test_load_from_registry_marks_load_and_contract_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_loader(path: str) -> object:
        if path == "test.plugins:load_error":
            raise ValueError("broken class path")
        if path == "test.plugins:no_classifier":
            return _NoClassifierMethodPlugin()
        if path == "test.plugins:ok":
            return _AppendTitleIngestPlugin()
        raise AssertionError(f"Unexpected class path: {path}")

    monkeypatch.setattr(plugin_manager_module, "_load_plugin", fake_loader)

    manager = PluginManager()
    manager.load_from_registry(
        [
            _entry(plugin_id="load_error", class_path="test.plugins:load_error", capabilities=["ingest_hook"]),
            _entry(
                plugin_id="missing_method", class_path="test.plugins:no_classifier", capabilities=["stream_classifier"]
            ),
            _entry(plugin_id="ok_ingest", class_path="test.plugins:ok", capabilities=["ingest_hook"]),
        ]
    )

    assert manager.names() == ["ok_ingest"]
    snapshots = {item.plugin_id: item for item in manager.get_status_snapshots()}

    assert snapshots["load_error"].loaded is False
    assert snapshots["load_error"].startup_validation_status == "load_error"
    assert snapshots["load_error"].unavailable_reason is not None

    assert snapshots["missing_method"].loaded is False
    assert snapshots["missing_method"].startup_validation_status == "invalid_capability_impl"
    assert "requires callable" in (snapshots["missing_method"].unavailable_reason or "")

    assert snapshots["ok_ingest"].loaded is True
    assert snapshots["ok_ingest"].startup_validation_status == "ok"

    assert snapshots["ok_ingest"].last_updated_at <= datetime.now(UTC)
