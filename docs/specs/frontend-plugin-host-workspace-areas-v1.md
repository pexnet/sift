# Frontend Plugin Host and Workspace Areas v1

## Status

- State: In Progress
- Scope: Baseline host runtime + workspace plugin area routing/nav implemented
- Backlog reference: [docs/backlog.md](../backlog.md)
- Parent dependency: [docs/specs/plugin-platform-foundation-v1.md](plugin-platform-foundation-v1.md)

## Context

Architecture documents frontend extension points, but current frontend runtime does not yet host plugin UI modules or
render a dedicated plugin area section in workspace navigation.

## Goals

1. Implement a typed frontend plugin host runtime with registration validation.
2. Render a dedicated `Plugins` section in workspace navigation from enabled registry entries.
3. Mount plugin area views inside the workspace shell with failure isolation.
4. Preserve existing system/folder/feed/stream UX behavior unchanged.

## Non-Goals (v1)

1. No plugin marketplace UI.
2. No remote client-side plugin package loading.
3. No per-user plugin visibility toggle model.

## Implemented Checkpoint (2026-02-22)

1. Added frontend plugin area host runtime with registration validation:
   - duplicate ids are deterministically rejected (first valid registration wins)
   - invalid registrations are skipped
   - unknown optional capability flags are ignored with debug diagnostics
2. Added workspace plugin area API integration:
   - `GET /api/v1/plugins/areas` backend endpoint
   - frontend query hook + typed parsing for plugin area metadata
3. Added workspace plugin navigation section:
   - `Plugins` section renders enabled/loaded plugin areas
   - selecting a plugin row routes to `/app/plugins/$areaId`
4. Added plugin area route and host rendering:
   - `/app/plugins/$areaId` route keeps workspace shell/rail/navigation
   - plugin mounts render inside isolated error boundary with `Plugin unavailable` fallback
5. Added baseline plugin area mount:
   - `discover_feeds` placeholder area registered and mounted

## Host Runtime Contract

### Registration

1. Validate each plugin UI registration at startup.
2. Reject duplicate ids deterministically (first valid wins).
3. Ignore unknown optional capability flags with debug diagnostics.

### Isolation

1. Every plugin mount runs inside an error boundary.
2. Plugin render failure shows `Plugin unavailable` fallback.
3. Host shell and other plugin areas remain interactive after one plugin failure.

## Workspace Navigation IA

1. Add `Plugins` section in navigation under existing built-in sections.
2. Each enabled plugin area includes:
   - id
   - label
   - icon key
   - optional badge/count
   - route target
3. Disabled/unavailable plugins are hidden from nav.

## Routing Model

1. Add plugin area route branch in frontend router:
   - implemented: `/app/plugins/$areaId`
2. Keep existing `/app` route/search behavior unchanged for current scopes.
3. Preserve workspace shell layout and keyboard baseline in plugin area views.

## Backend Data Contract

Add read API:

1. `GET /api/v1/plugins/areas`
   - implemented; returns enabled UI area metadata for current deployment
   - includes nav ordering and visibility info only (no secrets)

Note:

1. Article/feed navigation APIs remain unchanged in this slice.
2. Plugin area cards/panels fetch plugin-owned data via their own APIs.

## Accessibility and UX Baseline

1. `Plugins` section rows are keyboard navigable like existing nav rows.
2. Icon-only controls require tooltip/`aria-label` parity.
3. Error fallback states are screen-reader visible and non-blocking.

## Acceptance Criteria

1. [x] Frontend can register and mount enabled plugin areas.
2. [x] Workspace nav shows `Plugins` section when one or more areas are enabled.
3. [x] Selecting plugin nav row loads plugin area route in workspace shell.
4. [x] Plugin render failures are isolated to affected mount.
5. [x] Existing non-plugin workspace routes/features remain unaffected.

## Test Plan

1. [x] Registration validation tests (duplicate ids, invalid registration).
2. [x] Router/route rendering tests for `/app/plugins/$areaId` behavior in workspace shell.
3. [x] Navigation tests for plugin section ordering/visibility.
4. [ ] Error-boundary tests for plugin failure fallback behavior.
5. [x] Regression tests for existing workspace navigation/list/reader flows.

## Rollout Notes

1. Start with one plugin area (`Discover feeds`) as baseline verification.
2. Add additional plugin areas incrementally after registry/runtime hardening slice.
3. Keep plugin host APIs and types fully internal until contracts stabilize.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related specs:
  - [docs/specs/plugin-ui-organization-v1.md](plugin-ui-organization-v1.md)
  - [docs/specs/plugin-platform-foundation-v1.md](plugin-platform-foundation-v1.md)
