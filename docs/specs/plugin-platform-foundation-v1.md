# Plugin Platform Foundation v1

## Status

- State: In Progress
- Scope: Backend foundation implementation started (registry + runtime cutover baseline complete)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Sift currently supports plugin hooks through path-based loading, but plugin activation/configuration and capability
boundaries are not yet standardized for long-term product growth (discovery, summaries, dashboard cards, future
integrations).

This slice establishes the canonical plugin platform contract and activation model used by backend and frontend.

## Goals

1. Define one canonical plugin activation/configuration source.
2. Define capability-oriented plugin contracts across ingest/classifier/discovery/summary/dashboard surfaces.
3. Ensure deterministic plugin registration with clear validation and failure behavior.
4. Use direct cutover and remove legacy plugin path activation/configuration behavior.

## Non-Goals (v1)

1. No plugin marketplace/distribution system.
2. No remote dynamic plugin config service.
3. No per-user plugin enable/disable model.
4. No runtime hot-reload guarantee for plugin modules.

## Locked Decisions

1. Centralized registry config is the only activation source in v1.
2. Direct cutover: no compatibility mode for legacy `plugin_paths`.
3. Plugin ids are stable/immutable and globally unique.
4. Capabilities are explicitly declared and validated at startup.
5. Invalid plugin entries fail fast with actionable field-path errors.

## Implemented Checkpoint (2026-02-22)

1. Added centralized plugin registry loader and schema validation in `src/sift/plugins/registry.py`.
2. Added canonical registry file `config/plugins.yaml` with first-party built-in entries.
3. Cut over runtime plugin initialization to registry-driven loading (`SIFT_PLUGIN_REGISTRY_PATH` /
   `plugin_registry_path`).
4. Removed legacy `SIFT_PLUGIN_PATHS`/`plugin_paths` from active runtime behavior.
5. Updated plugin manager dispatch to capability-gated execution by registry plugin id.
6. Added regression tests for registry validation and runtime cutover:
   - `tests/test_plugin_registry.py`
   - targeted stream/ingestion regression reruns

## Canonical Registry Model

Primary file: `config/plugins.yaml`

Top-level fields:

1. `version`
2. `plugins[]`

Per-plugin required fields:

1. `id`
2. `enabled`
3. `backend.class_path`
4. `capabilities`
5. `ui` metadata (when plugin has UI surface)
6. `settings`

Validation requirements:

1. Unique plugin ids.
2. Known capability names only (strict mode).
3. Known field-set only for each plugin type/capability.
4. Secrets referenced through environment variables, not plaintext literals.

## Capability Contract Baseline

Planned capability keys:

1. `ingest_hook`
2. `stream_classifier`
3. `discover_feeds`
4. `summarize_article`
5. `dashboard_card`
6. `workspace_area`
7. `command_palette_action`

Execution rule:

1. Capability missing -> no dispatch attempt.
2. Capability present but disabled/invalid -> plugin marked unavailable with reason.

## Startup and Registration Behavior

1. Load and validate registry.
2. Build deterministic plugin registration order.
3. Register enabled/valid plugins only.
4. Persist in-memory status for diagnostics (`enabled`, `loaded`, `disabled_reason`, `capabilities`).
5. Block startup only for fatal registry/schema errors.

## API and Runtime Interfaces

1. Runtime config source:
   - implemented: `config/plugins.yaml` (path configurable via `SIFT_PLUGIN_REGISTRY_PATH`)
2. Legacy config removal:
   - implemented: `SIFT_PLUGIN_PATHS`/`plugin_paths` removed from active runtime behavior
3. Plugin status surface (implemented by companion diagnostics spec):
   - `GET /api/v1/plugins/status`

## Acceptance Criteria

1. [x] Plugin activation is driven only by registry config.
2. [x] Legacy path-list activation is removed from runtime behavior.
3. [x] Registry validation reports clear plugin id + field path errors.
4. [ ] Enabled/disabled states are deterministic and observable via diagnostics.
5. [x] Existing built-in ingest/classifier plugin behavior remains functionally intact after cutover.

## Test Plan

1. [x] Registry schema validation tests (valid and invalid samples).
2. [ ] Startup tests for deterministic ordering and enable/disable behavior.
3. [x] Regression tests ensuring ingest/classifier dispatch still works post-cutover.
4. [ ] Config security tests for env-ref handling and forbidden plaintext secret fields.

## Rollout Notes

1. Deliver this as a strict cutover in one feature slice.
2. Update `.env.example` and runtime docs to remove legacy plugin-path configuration.
3. Keep first-party plugins registered via new registry file from day one.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related specs:
  - [docs/specs/plugin-configuration-registry-v1.md](plugin-configuration-registry-v1.md)
  - [docs/specs/plugin-ui-organization-v1.md](plugin-ui-organization-v1.md)
