# Plugin Configuration Registry v1 (Centralized Config + Enable/Disable)

## Status

- State: In Progress
- Scope: Centralized registry baseline, diagnostics read API, and security/budget contract validation implemented
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Plugin behavior is currently configured through scattered settings and path lists. This spec defines a centralized
configuration model so plugin setup is easy to modify and plugins can be turned on/off without code edits.

## Goal

Provide one source of truth for plugin configuration that includes:

1. Plugin registration metadata.
2. Per-plugin enable/disable toggles.
3. Plugin-specific settings payloads.
4. UI metadata used by workspace plugin folders/areas.

## Non-Goals (v1)

1. No remote configuration service.
2. No per-user plugin toggle model (v1 is system-level/global).
3. No runtime hot-reload guarantee for all plugins.

## Implemented Baseline Configuration Shape

Primary file: `config/plugins.yaml` (runtime override: `SIFT_PLUGIN_REGISTRY_PATH`).

Top-level structure:

1. `version`
2. `plugins[]` entries with:
   - `id` (stable key)
   - `enabled` (boolean)
   - `backend.class_path` (plugin loader target)
   - `capabilities` (validated capability list)
   - `ui.area` metadata (title/icon/order/route key)
   - `settings` (plugin-specific object)

Example logical entries:

1. `search_provider`:
   - enabled true/false
   - provider chain (`searxng`, `brave_search`, optional adapters)
   - provider credentials/env references
   - provider budgets and limits:
     - `max_requests_per_run`
     - `max_requests_per_day`
     - `min_interval_ms`
     - `max_query_variants_per_stream`
     - `max_results_per_query`
   - fallback policy and timeout settings
2. `discover_feeds`:
   - enabled true/false
   - discovery workflow settings (stream generation/recommendation behavior)
   - consumes shared provider execution via `search_provider` capability
   - UI area label `Discover feeds`
3. `bluesky`:
   - enabled true/false
   - auth/api parameters
   - UI area label `Bluesky`

## Runtime Behavior

1. [x] App startup loads centralized plugin config.
2. [x] Only enabled plugins are instantiated/registered.
3. Disabled plugins:
   - [x] backend hooks are skipped
   - [x] UI areas are hidden from `/api/v1/plugins/areas` and workspace plugin navigation
4. [x] Validation errors fail with actionable messages (field-path details; plugin id included where applicable).
5. [x] Search-provider settings contract enforces provider budget/rate-limit fields at registry validation time.
6. [ ] Budget exhaustion produces partial results with explicit warning metadata (no silent overage).

## Implemented Checkpoint (2026-02-22)

1. Added strict security validation for sensitive settings keys:
   - sensitive values must be environment variable references (for example `${SIFT_API_KEY}`)
   - plaintext secret/token/password/api-key values are rejected at registry validation time
2. Added search-provider budget contract validation (current runtime path uses discover-feeds settings shape and will
   be expanded in follow-up):
   - validates provider-chain shape
   - validates per-provider budget fields:
     - `max_requests_per_run`
     - `max_requests_per_day`
     - `min_interval_ms`
     - `max_query_variants_per_stream`
     - `max_results_per_query`
   - validates `max_requests_per_day >= max_requests_per_run`
3. Added registry tests for:
   - sensitive settings env-ref enforcement
   - valid/invalid provider budget contract scenarios

## API and Admin Surface (Future Direction)

Phase 1:

1. File-driven config only (no admin write API).
2. [x] Read-only diagnostics endpoint is available (`GET /api/v1/plugins/status`).

Future phase:

1. Optional admin UI/API for editing plugin registry safely.

## Security and Safety Notes

1. Sensitive values (API keys/secrets) should be referenced via environment variables, not plaintext in repo files.
2. Config parser must enforce allowed fields and reject unknown critical keys in strict mode.
3. Plugin ids must be unique and immutable once created.

## Acceptance Criteria

1. [x] Plugin registry is loaded from one configuration file.
2. [x] Enabling/disabling a plugin changes both backend activation and UI visibility.
3. [x] Discover feeds and future plugin entries can be toggled independently.
4. [x] Invalid registry entries produce clear startup/validation errors.
5. [x] Search-provider plugin config can enforce free-tier-safe request budget contracts without code changes.

## Test Plan

1. [x] Config schema validation tests (valid/invalid files).
2. [x] Runtime tests for enabled vs disabled plugin registration.
3. [ ] UI navigation tests confirming hidden/visible plugin areas based on toggles.
4. [x] Regression tests for existing plugin manager behavior.
5. [x] Search-provider budget/rate-limit config contract tests (schema and bounds validation).
6. [ ] Deferred runtime behavior tests for cap exhaustion and partial-result warning metadata.

## Rollout Notes

1. [x] Direct cutover applied: centralized registry is now the only active plugin activation/config source.
2. [x] Legacy `plugin_paths` activation/configuration support removed from active runtime path.
3. [ ] Migrate all first-party plugins (built-ins completed for current scope: `noop`,
   `keyword_heuristic_classifier`; discovery/future Bluesky entries remain future scope).

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
