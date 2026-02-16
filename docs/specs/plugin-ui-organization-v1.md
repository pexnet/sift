# Plugin UI Organization v1 (Per-Plugin Workspace Areas)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Sift already supports plugin-capable backend workflows, but workspace UI structure for plugin-specific experiences is not
standardized. This spec defines a UI organization model where each plugin gets its own dedicated workspace area/folder.

Examples from current product ideas:

1. Feed recommendation features should appear in a dedicated `Recommended feeds` area.
2. A future Bluesky integration should appear in a dedicated `Bluesky` area.

## Goal

Define a predictable UI information architecture for plugin features so users can discover and manage plugin outputs
without mixing them into unrelated core areas.

## Non-Goals (v1)

1. No plugin marketplace/distribution system.
2. No full plugin permission model redesign.
3. No implementation of specific plugin business logic in this spec.

## Proposed UI Information Architecture

1. Introduce a `Plugins` section in workspace navigation (left pane).
2. Each enabled plugin can register one or more top-level plugin folders/areas.
3. Each area has:
   - id (stable plugin-scoped key)
   - display name
   - icon key
   - unread/pending count (optional)
   - route/view target
4. Core examples:
   - `recommended_feeds` (from recommendation plugin)
   - `bluesky` (from Bluesky plugin when enabled)

## Plugin Folder Naming Rules

1. User-facing labels should be short and product-specific.
2. Internal ids must be namespaced by plugin id (for example, `plugin.recommended_feeds.main`).
3. Ordering is deterministic and configurable from plugin config.

## Route/View Model (Planned)

1. Route state must support plugin areas as first-class scopes.
2. Workspace should switch panes/views when selecting plugin areas.
3. Plugin areas should preserve existing workspace shell behavior (density, theme, keyboard baseline).

## UX and Accessibility Baseline

1. Keep visible labels for plugin areas; icons are additive.
2. Provide `aria-label` and tooltip parity for icon-heavy controls.
3. Maintain keyboard navigation parity with existing system/folder/feed/stream sections.

## Acceptance Criteria (for later implementation)

1. Plugin areas are visible in a dedicated workspace `Plugins` nav section.
2. Recommended feeds appears in its own area when recommendation plugin is enabled.
3. Bluesky appears in its own area when Bluesky plugin is enabled.
4. Disabled plugins do not render nav areas.
5. Existing core workspace scopes continue to function unchanged.

## Test Plan (for later implementation)

1. Navigation model tests for plugin area mapping and ordering.
2. Workspace route tests for plugin-scope selection/rendering.
3. Accessibility tests for keyboard and labels.
4. Regression tests for existing nav/list/reader behavior.

## Rollout Notes

1. Deliver behind feature branch and progressive plugin-by-plugin adoption.
2. Start with `Recommended feeds` as first plugin-area implementation.
3. Add Bluesky area only when Bluesky plugin backend/UI slices are ready.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
