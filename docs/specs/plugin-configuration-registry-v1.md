# Plugin Configuration Registry v1 (Centralized Config + Enable/Disable)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
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

## Proposed Configuration Shape

Primary file (proposed path): `config/plugins.yaml` (or equivalent JSON/TOML if stack constraints require).

Top-level structure:

1. `version`
2. `plugins[]` entries with:
   - `id` (stable key)
   - `enabled` (boolean)
   - `backend.class_path` (plugin loader target)
   - `ui.area` metadata (title/icon/order/route key)
   - `settings` (plugin-specific object)

Example logical entries:

1. `recommended_feeds`:
   - enabled true/false
   - provider keys and generation limits
   - UI area label `Recommended feeds`
2. `bluesky`:
   - enabled true/false
   - auth/api parameters
   - UI area label `Bluesky`

## Runtime Behavior (Planned)

1. App startup loads centralized plugin config.
2. Only enabled plugins are instantiated/registered.
3. Disabled plugins:
   - backend hooks are skipped
   - UI areas are hidden
4. Validation errors should fail with actionable messages (plugin id + field path).

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

## Acceptance Criteria (for later implementation)

1. Plugin registry is loaded from one configuration file.
2. Enabling/disabling a plugin changes both backend activation and UI visibility.
3. Recommended feeds and Bluesky plugin entries can be toggled independently.
4. Invalid registry entries produce clear startup/validation errors.

## Test Plan (for later implementation)

1. Config schema validation tests (valid/invalid files).
2. Runtime tests for enabled vs disabled plugin registration.
3. UI navigation tests confirming hidden/visible plugin areas based on toggles.
4. Regression tests for existing plugin manager behavior.

## Rollout Notes

1. Start with compatibility mode: map existing `plugin_paths` settings into registry defaults.
2. Introduce explicit deprecation window for legacy plugin path config.
3. Migrate first-party plugins (noop/classifier/recommendations/future Bluesky) to registry entries.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
