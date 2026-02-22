# Feed Health + Edit Surface v1

## Status

- State: Implemented (2026-02-19)
- Scope: Completed backend + frontend vertical slice (`/account/feed-health` + feed lifecycle/health APIs)
- Backlog reference: [docs/backlog-history.md](../../backlog-history.md)
- Related dashboard dependency spec: [docs/specs/feed-health-ops-panel-v1.md](../feed-health-ops-panel-v1.md)

## Context

Sift already tracks feed fetch metadata (`last_fetched_at`, `last_fetch_error`) but lacked:

1. a dedicated feed-health management page in settings, and
2. explicit lifecycle controls for pause/archive behavior.

## Goal

Deliver an authenticated feed-health/edit surface with:

1. per-feed health visibility (stale/error/cadence/unread),
2. lifecycle actions (pause/resume/archive/unarchive), and
3. fetch interval editing.

## Scope

### In Scope (v1)

1. `GET /api/v1/feeds/health`
2. `PATCH /api/v1/feeds/{feed_id}/settings`
3. `PATCH /api/v1/feeds/{feed_id}/lifecycle`
4. `GET /api/v1/feeds` support for `include_archived`
5. `/account/feed-health` frontend route and management UI
6. archive side effect: mark existing unread articles from that feed as read

### Out of Scope (v1)

1. Dashboard feed-health card endpoint (`/api/v1/dashboard/cards/feed-health`)
2. ingest run-history table
3. deep historical charts/analytics

## Lifecycle Rules

1. `pause`: allowed only when feed is not archived; sets `is_active=false`.
2. `resume`: allowed only when feed is not archived; sets `is_active=true`.
3. `archive`: sets `is_archived=true`, `is_active=false`, `archived_at=now`, and marks unread feed articles as read.
4. `unarchive`: sets `is_archived=false`, `archived_at=null`, and restores `is_active=true`.
5. repeated same action is idempotent.

## Health Rules

1. Lifecycle status:
   - `archived` when `is_archived=true`
   - `paused` when `is_archived=false` and `is_active=false`
   - `active` when `is_archived=false` and `is_active=true`
2. Staleness applies only to active feeds.
3. Stale threshold:
   - stale when `last_fetch_success_at` is null, or
   - stale when age exceeds `max(6 hours, 4 * fetch_interval_minutes)`.
4. Cadence:
   - `articles_last_7d` from `coalesce(published_at, created_at)`.
   - `estimated_articles_per_day_7d = round(articles_last_7d / 7, 2)`.

## Data Model

`feeds` additions:

1. `is_archived` (bool, default false, indexed)
2. `archived_at` (timestamp nullable)
3. `last_fetch_success_at` (timestamp nullable)
4. `last_fetch_error_at` (timestamp nullable)

Backfill rules:

1. set `last_fetch_success_at = last_fetched_at` when last fetch had no error
2. set `last_fetch_error_at = last_fetched_at` when last fetch has error text

## API Contracts

1. `GET /api/v1/feeds/health`
   - query: `lifecycle`, `q`, `stale_only`, `error_only`, `limit`, `offset`
   - response: `FeedHealthListResponse`
2. `PATCH /api/v1/feeds/{feed_id}/settings`
   - request: `FeedSettingsUpdate` (`fetch_interval_minutes`)
3. `PATCH /api/v1/feeds/{feed_id}/lifecycle`
   - request: `FeedLifecycleUpdate` (`pause|resume|archive|unarchive`)
   - response: `FeedLifecycleResultOut` (`feed`, `marked_read_count`)

## Frontend Surface

1. New authenticated route: `/account/feed-health`
2. Account settings entry link: `Manage feed health`
3. Per-feed controls:
   - fetch interval edit/save
   - pause/resume
   - archive/unarchive
4. Filters:
   - lifecycle
   - stale-only
   - error-only
   - text search
5. Archive action includes explicit unread-marking confirmation copy.

## Validation + Errors

1. `404` for feed not found/not owned.
2. `400` for invalid lifecycle transitions.
3. `400` for invalid `fetch_interval_minutes` range.

## Verification Targets

Backend:

1. lifecycle transition behavior + idempotence
2. stale/cadence/unread calculations
3. feed-health API auth + contract + mutation behavior

Frontend:

1. route render + filtering controls
2. interval update and lifecycle mutation flows
3. archive confirmation and marked-read feedback

## Implementation Summary

1. Added feed lifecycle/fetch metadata columns and migration backfill:
   - `is_archived`
   - `archived_at`
   - `last_fetch_success_at`
   - `last_fetch_error_at`
2. Implemented lifecycle and health APIs:
   - `GET /api/v1/feeds/health`
   - `PATCH /api/v1/feeds/{feed_id}/settings`
   - `PATCH /api/v1/feeds/{feed_id}/lifecycle`
   - `GET /api/v1/feeds` now supports `include_archived`
3. Implemented `/account/feed-health` UI with lifecycle controls, interval editing, filters, and archive confirmation.
4. Implemented archive side effect to bulk-mark existing unread articles from the feed as read.
5. Verified with backend/frontend tests and quality gates during implementation session.

## Backlog References

- Backlog history: [docs/backlog-history.md](../../backlog-history.md)
- Feed health ops dashboard dependency spec: [docs/specs/feed-health-ops-panel-v1.md](../feed-health-ops-panel-v1.md)
