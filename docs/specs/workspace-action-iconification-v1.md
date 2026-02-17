# Workspace Action Iconification v1 (Icons + Tooltips + A11y Labels)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Workspace actions are currently mostly text buttons (for example `Mark read`, `Save`, `Open original`,
`Mark all in scope as read`, `Prev`, `Next`). This is functional but visually heavy in compact layouts and less aligned
with the broader icon-forward workspace polish already applied in navigation/top-bar areas.

## Goal

Introduce a consistent icon-first action model for workspace controls while preserving clarity and accessibility through:

1. explicit tooltips
2. robust `aria-label` semantics
3. keyboard parity

## Non-Goals (v1)

1. No change to the underlying action behavior, API calls, or keyboard shortcuts.
2. No command palette redesign.
3. No removal of critical textual context in evidence and metadata surfaces.

## Scope (Planned)

### In Scope

1. Article list controls:
   - `Mark all in scope as read`
2. Reader action row:
   - `Mark read` / `Mark unread`
   - `Save` / `Unsave`
   - `Open original`
   - `Prev` / `Next`
   - `Hide highlights` / `Show highlights`
3. Optional row-level quick actions if currently text-heavy in active view.

### Out of Scope (v1)

1. Monitoring feed definition form controls.
2. Settings page control redesign.
3. Navigation tree node rendering changes (already icon-polished in prior slices).

## UX Design Rules

1. Use `IconButton` + `Tooltip` for primary compact actions.
2. Maintain deterministic icon semantics:
   - open/link icon for external open
   - bookmark/star icon for save
   - eye/check icon for read state
   - chevrons/arrows for prev/next
3. Tooltip copy should include action intent and shortcut hint where relevant.
   - Example: `Mark as read (m)`
4. Keep disabled-state tooltips informative when possible.
5. Preserve responsive behavior:
   - icon-first layout on desktop/tablet
   - avoid crowded rows on narrow mobile widths.

## Accessibility Requirements

1. Every icon action must have explicit `aria-label`.
2. Tooltip text must match or clarify `aria-label`.
3. Focus-visible styling must remain obvious at keyboard navigation.
4. Touch target minimum should remain practical (for example ~40px hit area).
5. Existing keyboard shortcuts must continue to work unchanged.

## Proposed Interaction Copy Map

1. `Mark read` / `Mark unread`:
   - tooltip: `Mark as read (m)` / `Mark as unread (m)`
2. `Save` / `Unsave`:
   - tooltip: `Save article (s)` / `Remove from saved (s)`
3. `Open original`:
   - tooltip: `Open original source (o)`
4. `Prev` / `Next`:
   - tooltip: `Previous article (k)` / `Next article (j)`
5. `Hide highlights` / `Show highlights`:
   - tooltip: `Hide match highlights` / `Show match highlights`
6. `Mark all in scope as read`:
   - tooltip: `Mark all articles in current scope as read`

## Implementation Approach (Planned)

1. Create shared action descriptor model per pane (id, icon, tooltip, aria-label, disabled logic).
2. Replace text buttons with icon buttons for in-scope actions.
3. Keep selected high-risk actions with optional textual fallback where clarity is critical.
4. Update tests to assert:
   - button discoverability by role/label
   - tooltip copy
   - no regression in click behavior.

## Acceptance Criteria (for later implementation)

1. In-scope workspace actions are icon-first with tooltips.
2. All icon actions expose clear `aria-label` values.
3. Existing action behavior and keyboard shortcuts are unchanged.
4. Reader/list layouts remain stable across compact and mobile scenarios.
5. Existing tests are updated and pass with no functional regressions.

## Test Plan (for later implementation)

Frontend:

1. Component tests for icon button rendering and labels/tooltips in:
   - `ArticlesPane`
   - `ReaderPane`
2. Shortcut tests to ensure iconification does not break keyboard flows.
3. Visual regression smoke checks for compact vs comfortable density.

## Rollout Notes

1. Ship as a focused UX slice without backend changes.
2. If user feedback indicates discoverability drop, add preference toggle for icon+text fallback mode.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
