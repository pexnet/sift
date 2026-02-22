import logging
import re
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

_ENV_REF_PATTERN = re.compile(r"^\$\{[A-Z][A-Z0-9_]*\}$")
_SENSITIVE_SETTING_TOKENS = (
    "secret",
    "token",
    "password",
    "apikey",
    "accesskey",
    "privatekey",
)
_DISCOVERY_BUDGET_FIELDS = (
    "max_requests_per_run",
    "max_requests_per_day",
    "min_interval_ms",
    "max_query_variants_per_stream",
    "max_results_per_query",
)


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

    @model_validator(mode="after")
    def validate_settings_contract(self) -> "PluginRegistryEntry":
        errors = _collect_sensitive_settings_errors(settings=self.settings, path="settings")
        if "discover_feeds" in self.capabilities:
            errors.extend(_collect_discovery_settings_errors(self.settings))
        if errors:
            details = "; ".join(errors)
            raise ValueError(f"plugin '{self.id}' settings validation failed: {details}")
        return self


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


def _collect_sensitive_settings_errors(*, settings: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    for key, value in settings.items():
        key_path = f"{path}.{key}"
        normalized_key = _normalize_key_token(key)
        if _is_sensitive_key(normalized_key):
            if not isinstance(value, str) or not _ENV_REF_PATTERN.match(value.strip()):
                errors.append(f"{key_path}: sensitive values must reference env vars (for example '${{SIFT_API_KEY}}')")
        if isinstance(value, dict):
            errors.extend(_collect_sensitive_settings_errors(settings=value, path=key_path))
            continue
        if isinstance(value, list):
            for index, item in enumerate(value):
                item_path = f"{key_path}[{index}]"
                if isinstance(item, dict):
                    errors.extend(_collect_sensitive_settings_errors(settings=item, path=item_path))
    return errors


def _normalize_key_token(key: str) -> str:
    return "".join(char for char in key.lower() if char.isalnum())


def _is_sensitive_key(normalized_key: str) -> bool:
    return any(token in normalized_key for token in _SENSITIVE_SETTING_TOKENS)


def _collect_discovery_settings_errors(settings: dict[str, Any]) -> list[str]:
    if not settings:
        return []
    raw_discovery = settings.get("discover_feeds")
    if raw_discovery is None:
        return []
    if not isinstance(raw_discovery, dict):
        return ["settings.discover_feeds: must be a mapping object"]

    errors: list[str] = []
    provider_chain = raw_discovery.get("provider_chain")
    if provider_chain is not None:
        if not isinstance(provider_chain, list) or not provider_chain:
            errors.append("settings.discover_feeds.provider_chain: must be a non-empty list when provided")
        elif not all(isinstance(item, str) and item.strip() for item in provider_chain):
            errors.append("settings.discover_feeds.provider_chain: entries must be non-empty strings")

    provider_budgets = raw_discovery.get("provider_budgets")
    if provider_budgets is not None:
        if not isinstance(provider_budgets, dict) or not provider_budgets:
            errors.append("settings.discover_feeds.provider_budgets: must be a non-empty mapping when provided")
            return errors
        for provider, budget in provider_budgets.items():
            provider_path = f"settings.discover_feeds.provider_budgets.{provider}"
            if not isinstance(provider, str) or not provider.strip():
                errors.append(f"{provider_path}: provider key must be a non-empty string")
                continue
            if not isinstance(budget, dict):
                errors.append(f"{provider_path}: budget config must be a mapping object")
                continue
            for field in _DISCOVERY_BUDGET_FIELDS:
                value = budget.get(field)
                field_path = f"{provider_path}.{field}"
                if not isinstance(value, int) or value < 1:
                    errors.append(f"{field_path}: must be an integer >= 1")
            max_per_run = budget.get("max_requests_per_run")
            max_per_day = budget.get("max_requests_per_day")
            if isinstance(max_per_run, int) and isinstance(max_per_day, int) and max_per_day < max_per_run:
                errors.append(f"{provider_path}.max_requests_per_day: must be >= max_requests_per_run")
    return errors


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
