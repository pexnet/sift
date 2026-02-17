# Silent Feeds v1 (Monitoring-Only Feed Mode)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Some feeds are valuable for monitoring-stream signal generation but are too noisy for direct reader workflows. This
spec defines a feed-level `silent` mode where ingestion and monitoring matching continue normally while unread pressure
is suppressed for that feed.

This document is a planning artifact and does not change backend/frontend behavior yet.

## Goal

Provide a monitoring-only mode for selected feeds:

1. User can mark a feed as `silent`.
2. Silent feeds still ingest articles and run monitoring stream matching exactly as normal feeds.
3. Articles ingested from silent feeds are automatically treated as read for the feed owner.
4. Silent feeds do not accumulate unread counts.

## Non-Goals (v1)

1. No change to monitoring stream matching logic or classifier behavior.
2. No deletion, suppression, or retention changes for article payloads.
3. No per-stream silent mode (v1 is feed-level only).
4. No cross-user/global silent feed settings.
5. No ranking model changes.

## Proposed Product Behavior

Definition:

- `silent feed`: a feed that is used for ingestion and monitoring population but should not produce unread backlog.

Behavior:

1. Ingest path:
   - fetch/parse/dedupe/persist continue unchanged.
   - monitoring stream matching and evidence generation continue unchanged.
   - after ingest persistence, user article state for ingested articles from silent feed is set/read as `read`.
2. Existing unread handling:
   - when a feed is switched from non-silent to silent, existing unread articles for that feed are bulk-marked read.
3. Unsilence behavior:
   - turning silent off stops auto-read behavior for future ingest.
   - previously auto-read articles are not automatically reverted to unread.
4. Navigation/list impact:
   - unread counts for silent feeds are expected to stay at zero after ingest/toggle processing.

## Proposed Data Model Changes

Table: `feeds`

Proposed field additions:

- `is_silent` (boolean, required, default `false`, indexed)

Constraints and indexes:

1. Index `(owner_id, is_silent)`.

## Proposed API Changes

1. Extend feed create/read payloads to include `is_silent`.
2. Add silent toggle endpoint:
   - `PATCH /api/v1/feeds/{feed_id}/silent`
   - payload: `{ "is_silent": true | false }`
   - when setting `true`, execute bulk mark-read for existing unread rows for that feed owner/feed pair.
3. Existing feed ingest endpoint remains unchanged:
   - `POST /api/v1/feeds/{feed_id}/ingest`
   - internally applies silent auto-read behavior if `is_silent=true`.

## UX Scope (Planned)

1. Add `Silent feed (monitoring-only)` toggle in feed management surfaces.
2. Show concise helper copy:
   - `New articles from this feed are auto-marked read, but monitoring rules still run.`
3. Optional badge on feed cards/list:
   - `Silent`

## Acceptance Criteria (for later implementation)

1. User can set/unset `is_silent` on owned feeds.
2. Silent feeds still produce monitoring matches and explainability evidence.
3. New articles from silent feeds are auto-read for the feed owner.
4. Switching a feed to silent bulk-marks existing unread for that feed as read.
5. Switching a feed from silent to non-silent does not retroactively change prior read states.
6. Existing ingestion/monitoring flows for non-silent feeds are unaffected.

## Test Plan (for later implementation)

Backend:

1. Service tests for silent toggle transitions and bulk mark-read side effects.
2. Ingest tests confirming stream matching still runs while article states are auto-read.
3. API tests for auth boundaries and silent toggle endpoint behavior.
4. Navigation/article listing tests confirming silent feed unread counts remain zero after ingest.

Frontend:

1. Feed management UI tests for silent toggle rendering and mutation wiring.
2. UX copy tests for monitoring-only helper text.
3. Regression tests for existing feed management and workspace behavior.

## Rollout Notes

1. Deliver as explicit feed-setting capability with migration-first schema update.
2. Keep default `is_silent=false` for backward compatibility.
3. If rollout needs isolation, guard UI exposure behind a feature flag while backend support lands.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)

