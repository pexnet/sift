# Plugin Configuration Registry v1 (Centralized Config + Enable/Disable)

## Status

- State: In Progress
- Scope: Backend file-driven registry baseline implemented; diagnostics/admin surface remains planned
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

1. `discover_feeds`:
   - enabled true/false
   - provider chain (`searxng`, `brave_search`, optional adapters)
   - provider credentials/env references
   - generation limits and provider budgets:
     - `max_requests_per_run`
     - `max_requests_per_day`
     - `min_interval_ms`
     - `max_query_variants_per_stream`
     - `max_results_per_query`
   - fallback policy and timeout settings
   - UI area label `Discover feeds`
2. `bluesky`:
   - enabled true/false
   - auth/api parameters
   - UI area label `Bluesky`

## Runtime Behavior

1. [x] App startup loads centralized plugin config.
2. [x] Only enabled plugins are instantiated/registered.
3. Disabled plugins:
   - [x] backend hooks are skipped
   - [ ] UI areas are hidden (frontend host slice pending)
4. [x] Validation errors fail with actionable messages (field-path details; plugin id included where applicable).
5. [ ] Discovery provider wrappers enforce configured per-provider budgets/rate limits before external calls.
6. [ ] Budget exhaustion produces partial results with explicit warning metadata (no silent overage).

## API and Admin Surface (Future Direction)

Phase 1:

1. File-driven config only (no admin write API).
2. Read-only diagnostics endpoint may be added later (`/api/v1/plugins/status`).

Future phase:

1. Optional admin UI/API for editing plugin registry safely.

## Security and Safety Notes

1. Sensitive values (API keys/secrets) should be referenced via environment variables, not plaintext in repo files.
2. Config parser must enforce allowed fields and reject unknown critical keys in strict mode.
3. Plugin ids must be unique and immutable once created.

## Acceptance Criteria

1. [x] Plugin registry is loaded from one configuration file.
2. [ ] Enabling/disabling a plugin changes both backend activation and UI visibility.
3. [ ] Discover feeds and Bluesky plugin entries can be toggled independently.
4. [x] Invalid registry entries produce clear startup/validation errors.
5. [ ] Discovery plugin config can enforce free-tier-safe request budgets without code changes.

## Test Plan

1. [x] Config schema validation tests (valid/invalid files).
2. [x] Runtime tests for enabled vs disabled plugin registration.
3. [ ] UI navigation tests confirming hidden/visible plugin areas based on toggles.
4. [x] Regression tests for existing plugin manager behavior.
5. [ ] Discovery budget/rate-limit config tests (cap enforcement and partial-result warning behavior).

## Rollout Notes

1. [x] Direct cutover applied: centralized registry is now the only active plugin activation/config source.
2. [x] Legacy `plugin_paths` activation/configuration support removed from active runtime path.
3. [ ] Migrate all first-party plugins (built-ins completed for current scope: `noop`,
   `keyword_heuristic_classifier`; discovery/future Bluesky entries remain future scope).

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
