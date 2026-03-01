from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PluginCapabilitySpec:
    required_method: str | None


CAPABILITY_SPECS: dict[str, PluginCapabilitySpec] = {
    "ingest_hook": PluginCapabilitySpec(required_method="on_article_ingested"),
    "stream_classifier": PluginCapabilitySpec(required_method="classify_stream"),
    "search_provider": PluginCapabilitySpec(required_method="search_feeds"),
    # Reserved dispatch capabilities for future slices; method contracts are enforced when runtime dispatch lands.
    "discover_feeds": PluginCapabilitySpec(required_method=None),
    "summarize_article": PluginCapabilitySpec(required_method=None),
    # Metadata/UI capabilities.
    "dashboard_card": PluginCapabilitySpec(required_method=None),
    "workspace_area": PluginCapabilitySpec(required_method=None),
    "command_palette_action": PluginCapabilitySpec(required_method=None),
}

VALID_PLUGIN_CAPABILITIES = frozenset(CAPABILITY_SPECS.keys())


def required_method_for_capability(capability: str) -> str | None:
    spec = CAPABILITY_SPECS.get(capability)
    if spec is None:
        return None
    return spec.required_method
