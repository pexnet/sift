import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import import_module
from time import perf_counter
from typing import Any, TypeVar

from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext
from sift.plugins.registry import PluginRegistryEntry

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_CAPABILITY_METHODS: dict[str, str] = {
    "ingest_hook": "on_article_ingested",
    "stream_classifier": "classify_stream",
}

_DEFAULT_TIMEOUTS_MS: dict[str, int] = {
    "ingest_hook": 2000,
    "stream_classifier": 3000,
    "discover_feeds": 5000,
    "summarize_article": 5000,
}


@dataclass(slots=True)
class LoadedPlugin:
    id: str
    capabilities: frozenset[str]
    implementation: Any


@dataclass(slots=True)
class CapabilityRuntimeCounters:
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0


@dataclass(slots=True)
class PluginRuntimeState:
    plugin_id: str
    enabled: bool
    loaded: bool
    capabilities: tuple[str, ...]
    startup_validation_status: str
    unavailable_reason: str | None
    last_error: str | None
    runtime_counters: dict[str, CapabilityRuntimeCounters] = field(default_factory=dict)
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class PluginStatusSnapshot:
    plugin_id: str
    enabled: bool
    loaded: bool
    capabilities: list[str]
    startup_validation_status: str
    last_error: str | None
    unavailable_reason: str | None
    runtime_counters: dict[str, dict[str, int]]
    last_updated_at: datetime


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


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _new_runtime_state(entry: PluginRegistryEntry) -> PluginRuntimeState:
    capabilities = tuple(sorted(entry.capabilities))
    return PluginRuntimeState(
        plugin_id=entry.id,
        enabled=entry.enabled,
        loaded=False,
        capabilities=capabilities,
        startup_validation_status="pending",
        unavailable_reason=None,
        last_error=None,
        runtime_counters={capability: CapabilityRuntimeCounters() for capability in capabilities},
        last_updated_at=_now_utc(),
    )


def _capability_contract_error(plugin: LoadedPlugin) -> str | None:
    for capability in plugin.capabilities:
        required_method = _CAPABILITY_METHODS.get(capability)
        if required_method is None:
            continue
        handler = getattr(plugin.implementation, required_method, None)
        if callable(handler):
            continue
        return f"Capability '{capability}' requires callable '{required_method}'"
    return None


class PluginManager:
    def __init__(
        self,
        *,
        timeout_ingest_ms: int = 2000,
        timeout_classifier_ms: int = 3000,
        timeout_discovery_ms: int = 5000,
        timeout_summary_ms: int = 5000,
        diagnostics_enabled: bool = True,
    ) -> None:
        self._plugins: list[LoadedPlugin] = []
        self._plugins_by_id: dict[str, LoadedPlugin] = {}
        self._runtime_states: dict[str, PluginRuntimeState] = {}
        self._state_order: list[str] = []
        self._diagnostics_enabled = diagnostics_enabled
        self._dispatch_failures_by_capability: dict[str, int] = {}
        self._capability_timeouts_ms: dict[str, int] = dict(_DEFAULT_TIMEOUTS_MS)
        self._capability_timeouts_ms["ingest_hook"] = max(1, timeout_ingest_ms)
        self._capability_timeouts_ms["stream_classifier"] = max(1, timeout_classifier_ms)
        self._capability_timeouts_ms["discover_feeds"] = max(1, timeout_discovery_ms)
        self._capability_timeouts_ms["summarize_article"] = max(1, timeout_summary_ms)

    def load_from_registry(self, plugins: list[PluginRegistryEntry]) -> None:
        self._plugins = []
        self._plugins_by_id = {}
        self._runtime_states = {}
        self._state_order = []
        self._dispatch_failures_by_capability = {}

        for entry in plugins:
            state = _new_runtime_state(entry)
            self._runtime_states[entry.id] = state
            self._state_order.append(entry.id)

            if not entry.enabled:
                state.startup_validation_status = "disabled"
                state.unavailable_reason = "disabled by configuration"
                state.last_updated_at = _now_utc()
                continue

            try:
                implementation = _load_plugin(entry.backend.class_path)
            except Exception as exc:  # noqa: BLE001
                reason = str(exc)
                state.startup_validation_status = "load_error"
                state.unavailable_reason = reason
                state.last_error = reason
                state.last_updated_at = _now_utc()
                logger.error(
                    "plugin.dispatch.error",
                    extra={
                        "event": "plugin.dispatch.error",
                        "plugin_id": entry.id,
                        "capability": "startup",
                        "result": "failure",
                        "duration_ms": 0,
                        "error_type": type(exc).__name__,
                        "error_message": reason,
                    },
                )
                continue

            plugin = LoadedPlugin(
                id=entry.id,
                capabilities=frozenset(entry.capabilities),
                implementation=implementation,
            )
            capability_error = _capability_contract_error(plugin)
            if capability_error:
                state.startup_validation_status = "invalid_capability_impl"
                state.unavailable_reason = capability_error
                state.last_error = capability_error
                state.last_updated_at = _now_utc()
                logger.error(
                    "plugin.dispatch.error",
                    extra={
                        "event": "plugin.dispatch.error",
                        "plugin_id": entry.id,
                        "capability": "startup",
                        "result": "failure",
                        "duration_ms": 0,
                        "error_type": "CapabilityContractError",
                        "error_message": capability_error,
                    },
                )
                continue

            state.startup_validation_status = "ok"
            state.loaded = True
            state.unavailable_reason = None
            state.last_updated_at = _now_utc()
            self._plugins.append(plugin)
            self._plugins_by_id[plugin.id] = plugin

    def names(self) -> list[str]:
        return [plugin.id for plugin in self._plugins]

    @property
    def diagnostics_enabled(self) -> bool:
        return self._diagnostics_enabled

    def _record_success(self, *, plugin_id: str, capability: str, duration_ms: int) -> None:
        state = self._runtime_states.get(plugin_id)
        if state is None:
            return
        counters = state.runtime_counters.setdefault(capability, CapabilityRuntimeCounters())
        counters.success_count += 1
        state.last_updated_at = _now_utc()
        logger.info(
            "plugin.dispatch.complete",
            extra={
                "event": "plugin.dispatch.complete",
                "plugin_id": plugin_id,
                "capability": capability,
                "result": "success",
                "duration_ms": duration_ms,
            },
        )

    def _record_failure(
        self,
        *,
        plugin_id: str,
        capability: str,
        duration_ms: int,
        error: Exception,
        timeout: bool,
    ) -> None:
        state = self._runtime_states.get(plugin_id)
        if state is None:
            return
        counters = state.runtime_counters.setdefault(capability, CapabilityRuntimeCounters())
        if timeout:
            counters.timeout_count += 1
        else:
            counters.failure_count += 1
        state.last_error = str(error)
        state.last_updated_at = _now_utc()
        self._dispatch_failures_by_capability[capability] = self._dispatch_failures_by_capability.get(capability, 0) + 1
        event_name = "plugin.dispatch.timeout" if timeout else "plugin.dispatch.error"
        logger.error(
            event_name,
            extra={
                "event": event_name,
                "plugin_id": plugin_id,
                "capability": capability,
                "result": "timeout" if timeout else "failure",
                "duration_ms": duration_ms,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

    async def _invoke_plugin(
        self,
        *,
        plugin: LoadedPlugin,
        capability: str,
        callback: Callable[[], Awaitable[_T]],
    ) -> _T | None:
        start_time = perf_counter()
        logger.info(
            "plugin.dispatch.start",
            extra={
                "event": "plugin.dispatch.start",
                "plugin_id": plugin.id,
                "capability": capability,
                "result": "started",
                "duration_ms": 0,
            },
        )
        timeout_ms = self._capability_timeouts_ms.get(capability, 1000)
        try:
            result = await asyncio.wait_for(callback(), timeout=timeout_ms / 1000.0)
        except TimeoutError as exc:
            duration_ms = int((perf_counter() - start_time) * 1000)
            self._record_failure(
                plugin_id=plugin.id,
                capability=capability,
                duration_ms=duration_ms,
                error=exc,
                timeout=True,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((perf_counter() - start_time) * 1000)
            self._record_failure(
                plugin_id=plugin.id,
                capability=capability,
                duration_ms=duration_ms,
                error=exc,
                timeout=False,
            )
            return None
        duration_ms = int((perf_counter() - start_time) * 1000)
        self._record_success(plugin_id=plugin.id, capability=capability, duration_ms=duration_ms)
        return result

    def get_status_snapshots(self) -> list[PluginStatusSnapshot]:
        snapshots: list[PluginStatusSnapshot] = []
        for plugin_id in self._state_order:
            state = self._runtime_states.get(plugin_id)
            if state is None:
                continue
            runtime_counters = {
                capability: {
                    "success_count": counters.success_count,
                    "failure_count": counters.failure_count,
                    "timeout_count": counters.timeout_count,
                }
                for capability, counters in state.runtime_counters.items()
            }
            snapshots.append(
                PluginStatusSnapshot(
                    plugin_id=state.plugin_id,
                    enabled=state.enabled,
                    loaded=state.loaded,
                    capabilities=list(state.capabilities),
                    startup_validation_status=state.startup_validation_status,
                    last_error=state.last_error,
                    unavailable_reason=state.unavailable_reason,
                    runtime_counters=runtime_counters,
                    last_updated_at=state.last_updated_at,
                )
            )
        return snapshots

    async def run_ingested_hooks(self, article: ArticleContext) -> ArticleContext:
        current = article
        for plugin in self._plugins:
            if "ingest_hook" not in plugin.capabilities:
                continue
            on_article_ingested = getattr(plugin.implementation, "on_article_ingested", None)
            if callable(on_article_ingested):
                handler = on_article_ingested
                context = current

                async def ingest_callback(
                    handler: Callable[[ArticleContext], Awaitable[ArticleContext]] = handler,
                    context: ArticleContext = context,
                ) -> ArticleContext:
                    return await handler(context)

                next_context = await self._invoke_plugin(
                    plugin=plugin,
                    capability="ingest_hook",
                    callback=ingest_callback,
                )
                if isinstance(next_context, ArticleContext):
                    current = next_context
        return current

    async def classify_stream(
        self,
        *,
        plugin_name: str,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision | None:
        plugin = self._plugins_by_id.get(plugin_name)
        if plugin is None:
            return None
        if "stream_classifier" not in plugin.capabilities:
            return None
        classify_stream = getattr(plugin.implementation, "classify_stream", None)
        if not callable(classify_stream):
            return None
        handler = classify_stream

        async def classify_callback(
            handler: Callable[
                [ArticleContext, StreamClassifierContext],
                Awaitable[StreamClassificationDecision | None],
            ] = handler,
        ) -> StreamClassificationDecision | None:
            return await handler(article, stream)

        result = await self._invoke_plugin(
            plugin=plugin,
            capability="stream_classifier",
            callback=classify_callback,
        )
        if isinstance(result, StreamClassificationDecision):
            return result
        return None

