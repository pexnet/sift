# Workspace + Settings Management UI Touchups v1

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)
- UI reference direction: Inoreader-inspired dense operations layout (per user request, 2026-02-21)

## Context

Current UI behavior is functional, but several workflows are too verbose for daily feed triage:

1. Workspace navigation still uses text-heavy controls for folder/section actions.
2. Monitoring feeds are rendered as a flat list in navigation and in the management page.
3. Settings pages are connected by top-row buttons instead of a persistent side menu.
4. Monitoring feed management cards are too tall and reduce scanability.
5. Feed health uses large card blocks instead of condensed one-row operations.
6. Feed creation is missing from feed-health/workspace management flows.

## Goal

Deliver a dense, icon-forward management UX that keeps workflows fast:

1. Icon-only folder creation trigger (folder + plus icon).
2. Chevron-first expand/collapse controls that are immediately recognizable.
3. Folder organization for monitoring feeds (navigation + management workflow).
4. Side-menu settings shell across account/settings pages.
5. One-line monitoring rows with left-form edit population.
6. One-line feed-health rows with iconized per-feed operations.
7. Add-feed action integrated into settings/management flows.
8. Default "show all feeds" behavior in feed health.

## Non-Goals (v1)

1. No full visual redesign of the workspace shell.
2. No changes to ingest/scheduler runtime semantics.
3. No cross-user/global feed administration; all data stays user-scoped.
4. No dashboard (`/app/dashboard`) work in this slice.

## UX Decisions (Locked)

### 1) Workspace Navigation Controls

1. Replace the current text button `Folder` in navigation header with icon-only `CreateNewFolder` pattern.
2. Add tooltip and accessible label:
   - visible tooltip: `Add folder`
   - `aria-label`: `Add folder`
3. Keep folder create dialog behavior unchanged (name input + create action).
4. Replace text-based section collapse affordances with chevron icon controls:
   - monitoring section header: chevron toggle only
   - folder rows: chevron toggle (already present, retained)
5. Keep chevron orientation semantics:
   - right = collapsed
   - down = expanded

### 2) Monitoring Feed Folders

Use existing feed-folder objects for v1 to minimize surface area:

1. Add nullable `folder_id` to `keyword_streams`, referencing `feed_folders.id` with `ON DELETE SET NULL`.
2. Extend stream contracts (`create`, `update`, `out`) to include `folder_id`.
3. Validate on stream create/update that selected folder belongs to current user.
4. Navigation groups monitoring streams under folder headings (plus `Unfiled`).
5. Monitoring folder grouping order:
   - by folder `sort_order`, then folder name
   - unfiled group last
   - streams within group: by `priority`, then `name`
6. Monitoring section supports chevron collapse at folder-group level.

### 3) Settings Side Menu Shell

1. Introduce a reusable settings layout shell with:
   - left side menu on desktop
   - stacked/top menu on mobile
2. Menu entries:
   - `General` (`/account`)
   - `Feed health` (`/account/feed-health`)
   - `Monitoring feeds` (`/account/monitoring`)
   - `Help` (`/help`)
3. Remove top-of-page cross-links from each settings subpage; navigation comes from side menu.
4. Keep current URLs stable for direct links/bookmarks.

### 4) Monitoring Feed Management Density

1. Keep two-pane interaction model:
   - left: create/edit form
   - right: existing definitions
2. Right pane becomes one-row-per-stream dense list/table.
3. Each row includes:
   - active state toggle
   - stream name
   - folder label
   - mode
   - priority
   - query indicator
   - row actions (icon buttons): edit, backfill, delete
4. `Edit` action behavior:
   - populate left form with row values
   - preserve current validation rules
   - visually highlight active editing row
5. Remove always-expanded long metadata blocks from each row in default view.

### 5) Feed Health Dense Operations + Add Feed

1. Replace card stack with compact one-row-per-feed table/list.
2. Each feed row shows:
   - feed title (+ URL on secondary line)
   - lifecycle/status icons (active/paused/archived, stale, error)
   - unread count and 7d activity
   - last success and last error timestamps
   - inline interval input
   - icon actions for save interval, pause/resume, archive/unarchive
3. Replace verbose text action buttons with icon buttons + tooltips + explicit `aria-label`.
4. Add `Add feed` action in feed-health header (primary path).
5. Add-feed flow (dialog):
   - required: feed URL
   - optional: title override
   - optional: folder assignment
6. Default feed-health list behavior is all matching feeds at once (not first page only).

## API and Data Contract Plan

### 1) Database

1. Alembic migration:
   - add `keyword_streams.folder_id UUID NULL`
   - FK to `feed_folders.id` (`ON DELETE SET NULL`)
   - index on `keyword_streams.folder_id`

### 2) Stream APIs

1. Update `KeywordStreamCreate` with optional `folder_id`.
2. Update `KeywordStreamUpdate` with optional `folder_id`.
3. Update `KeywordStreamOut` with `folder_id`.
4. Keep endpoint paths unchanged:
   - `GET /api/v1/streams`
   - `POST /api/v1/streams`
   - `PATCH /api/v1/streams/{stream_id}`

### 3) Navigation API

1. Extend `NavigationStreamNodeOut` with `folder_id`.
2. `GET /api/v1/navigation` continues returning one payload, now stream-folder aware.

### 4) Feed Health API

1. Add query param `all` (bool, default `false`) to `GET /api/v1/feeds/health`.
2. When `all=true`, backend returns full filtered set and ignores `limit/offset`.
3. Keep existing `limit/offset` behavior for non-`all` clients.

### 5) Feed Create API

1. Extend `FeedCreate` with optional `folder_id` for one-shot add-and-assign flow.
2. Keep existing behavior valid when `folder_id` is omitted.

## Frontend Implementation Plan

### Workspace Navigation

1. `frontend/src/features/workspace/components/NavigationPane.tsx`
   - icon-only folder add button
   - chevron-only collapse controls
   - monitoring streams grouped by folder
2. `frontend/src/entities/navigation/model.ts`
   - add stream `folder_id` mapping
   - build monitoring folder hierarchy for render
3. `frontend/src/features/workspace/lib/navState.ts`
   - persist expanded/collapsed state for monitoring folder groups

### Settings Shell

1. `frontend/src/app/router.tsx`
   - introduce settings-shell route composition without breaking paths
2. `frontend/src/features/auth/routes/AccountPage.tsx`
   - render as "General" settings content inside shared shell
3. Add new shared settings layout component under `frontend/src/features/settings/` (new feature module)

### Monitoring Management

1. `frontend/src/features/monitoring/routes/MonitoringFeedsPage.tsx`
   - dense row/table rendering for stream list
   - edit action populates left form (existing behavior retained)
   - folder selection field in form
2. `frontend/src/features/monitoring/api/monitoringHooks.ts`
   - contract updates for stream `folder_id`

### Feed Health + Add Feed

1. `frontend/src/features/feed-health/routes/FeedHealthPage.tsx`
   - compact row layout
   - iconized lifecycle/settings actions
   - add-feed dialog and submit flow
2. `frontend/src/features/feed-health/api/feedHealthHooks.ts`
   - request `all=true` by default
3. `frontend/src/shared/api/workspaceApi.ts` or new feed API helper
   - add create-feed client call for dialog submission

### Styling

1. `frontend/src/app/styles.css`
   - add compact row and icon-action styles for monitoring/feed-health tables
   - maintain current theme preset token compatibility

## Acceptance Criteria

1. Workspace folder creation is triggered by folder-plus icon control (no text label required visually).
2. Expand/collapse controls for monitoring/folder sections are chevron-based and understandable without text.
3. Monitoring feeds can be assigned to folders and are rendered grouped by folder in workspace navigation.
4. Settings pages are navigable through a persistent side menu.
5. Monitoring management renders one row per stream; clicking edit populates left form.
6. Feed health renders one row per feed with icon-based operations.
7. Feed health can load all feeds in one view by default.
8. Add-feed button is present and creates a feed from the UI.

## Test Plan

### Backend

1. Migration test: `keyword_streams.folder_id` creation and FK behavior.
2. Stream API tests:
   - create/update with valid folder
   - reject foreign-user folder
3. Navigation service tests:
   - stream payload includes folder id
   - grouped ordering is deterministic
4. Feed health API tests:
   - `all=true` returns full filtered set
   - legacy paginated behavior still valid
5. Feed create API tests:
   - create with/without `folder_id`
   - ownership validation

### Frontend

1. `NavigationPane` tests:
   - icon-only add-folder control with accessible label
   - chevron collapse behavior
   - monitoring folder grouping render
2. `AccountPage`/settings-shell tests:
   - side menu links render and route correctly
3. `MonitoringFeedsPage` tests:
   - dense row rendering
   - edit button hydrates left form
   - folder field persistence
4. `FeedHealthPage` tests:
   - dense row actions
   - add-feed dialog success path
   - all-feeds query behavior

## Delivery Sequence

1. Backend schema + API contract updates (`folder_id`, feed-health `all`, feed create `folder_id`).
2. Frontend settings shell + workspace nav icon/chevron polish.
3. Monitoring dense row UI + folder assignment.
4. Feed-health dense row UI + add-feed flow.
5. Final polish, accessibility pass, and regression tests.

## Rollout Notes

1. Migration is additive and backward compatible (`folder_id` nullable).
2. Existing streams default to `Unfiled`.
3. Existing clients remain functional when new fields are ignored.
4. Ship behind normal `develop` integration flow; no feature flag required for v1.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Most recent completed related spec: [docs/specs/done/feed-health-edit-surface-v1.md](done/feed-health-edit-surface-v1.md)
