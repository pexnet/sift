import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

VALID_PLUGIN_CAPABILITIES = frozenset(
    {
        "ingest_hook",
        "stream_classifier",
        "discover_feeds",
        "summarize_article",
        "dashboard_card",
        "workspace_area",
        "command_palette_action",
    }
)

logger = logging.getLogger(__name__)


class PluginRegistryError(RuntimeError):
    pass


class PluginBackendConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_path: str = Field(min_length=3)


class PluginUIAreaConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    icon: str | None = Field(default=None, max_length=120)
    order: int = Field(default=100, ge=0, le=10_000)
    route_key: str | None = Field(default=None, max_length=120)


class PluginUIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: PluginUIAreaConfig | None = None


class PluginRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    enabled: bool = True
    backend: PluginBackendConfig
    capabilities: list[str] = Field(default_factory=list)
    ui: PluginUIConfig | None = None
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for capability in value:
            item = capability.strip()
            if item not in VALID_PLUGIN_CAPABILITIES:
                allowed = ", ".join(sorted(VALID_PLUGIN_CAPABILITIES))
                raise ValueError(f"Unknown capability '{item}'. Allowed: {allowed}")
            if item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized


class PluginRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    plugins: list[PluginRegistryEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "PluginRegistry":
        seen: set[str] = set()
        for entry in self.plugins:
            if entry.id in seen:
                raise ValueError(f"Duplicate plugin id '{entry.id}'")
            seen.add(entry.id)
        return self

    def enabled_plugins(self) -> list[PluginRegistryEntry]:
        return [entry for entry in self.plugins if entry.enabled]


def _resolve_registry_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (Path.cwd() / candidate).resolve()


def _format_validation_errors(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []))
        message = str(error.get("msg", "invalid value"))
        parts.append(f"{location}: {message}")
    return "; ".join(parts)


def load_plugin_registry(path: str) -> PluginRegistry:
    registry_path = _resolve_registry_path(path)
    if not registry_path.exists():
        logger.error(
            "plugin.registry.validation_error",
            extra={
                "event": "plugin.registry.validation_error",
                "plugin_id": None,
                "capability": "startup",
                "result": "failure",
                "duration_ms": 0,
                "error_type": "FileNotFoundError",
            },
        )
        raise PluginRegistryError(f"Plugin registry file not found: {registry_path}")

    try:
        raw_payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        logger.error(
            "plugin.registry.validation_error",
            extra={
                "event": "plugin.registry.validation_error",
                "plugin_id": None,
                "capability": "startup",
                "result": "failure",
                "duration_ms": 0,
                "error_type": type(exc).__name__,
            },
        )
        raise PluginRegistryError(f"Invalid YAML in plugin registry '{registry_path}': {exc}") from exc
    except OSError as exc:
        logger.error(
            "plugin.registry.validation_error",
            extra={
                "event": "plugin.registry.validation_error",
                "plugin_id": None,
                "capability": "startup",
                "result": "failure",
                "duration_ms": 0,
                "error_type": type(exc).__name__,
            },
        )
        raise PluginRegistryError(f"Failed reading plugin registry '{registry_path}': {exc}") from exc

    if raw_payload is None:
        raw_payload = {}
    if not isinstance(raw_payload, dict):
        logger.error(
            "plugin.registry.validation_error",
            extra={
                "event": "plugin.registry.validation_error",
                "plugin_id": None,
                "capability": "startup",
                "result": "failure",
                "duration_ms": 0,
                "error_type": "TypeError",
            },
        )
        raise PluginRegistryError(f"Plugin registry root must be a mapping object: {registry_path}")

    try:
        return PluginRegistry.model_validate(raw_payload)
    except ValidationError as exc:
        logger.error(
            "plugin.registry.validation_error",
            extra={
                "event": "plugin.registry.validation_error",
                "plugin_id": None,
                "capability": "startup",
                "result": "failure",
                "duration_ms": 0,
                "error_type": type(exc).__name__,
            },
        )
        details = _format_validation_errors(exc)
        raise PluginRegistryError(f"Plugin registry validation failed for '{registry_path}': {details}") from exc
