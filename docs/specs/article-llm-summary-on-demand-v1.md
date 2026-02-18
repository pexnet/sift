# Article LLM Summary On-Demand v1 (Plugin-Based Async Reader Action)

## Status

- State: Planned
- Scope: Specification only (no implementation in this checkpoint)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Current reader behavior focuses on feed-ingested article content and optional full-article fetch planning, but there is
no built-in on-demand summary capability.

We want an explicit reader action that can generate an article summary only when requested, while keeping LLM behavior
optional and safely disableable for deployments that do not have valid LLM provider configuration.

## Goal

Provide a user-triggered summary flow that:

1. runs on demand from the reader,
2. executes asynchronously with status tracking,
3. persists the latest summary per article for reuse,
4. uses plugin-based LLM execution that can be enabled/disabled by configuration.

## Non-Goals (v1)

1. No automatic summary generation for all ingested articles.
2. No per-user plugin enable/disable model (system-level capability in v1).
3. No summary version history (store latest only).
4. No arbitrary free-form user prompt input.

## UX

### Reader Action

1. Add `Generate summary` action in reader.
2. If a summary already exists, label switches to `Regenerate summary`.
3. Action is disabled while generation is pending.

### Reader Summary Card

1. Add summary card/section in reader showing status and results.
2. Structured output shape for v1:
   - `headline`
   - `key_points` (list)
   - `why_it_matters`
3. Show source badge (`full article` or `feed excerpt`) and provider/model metadata when available.

### Capability Unavailable Behavior

1. If no enabled/configured summary plugin is available, action remains visible but disabled.
2. Show inline hint/tooling text explaining missing plugin/config prerequisite.

### Input Source Policy

1. Prefer full-article content when available.
2. Fallback to feed excerpt/body content when full article is unavailable.

## Data Model

Add `article_summaries` table (latest-only, one row per article).

Proposed fields:

- `id` (UUID, primary key)
- `article_id` (UUID, unique FK -> `articles.id`, indexed)
- `status` (`idle` | `pending` | `succeeded` | `failed`, indexed)
- `headline` (string, nullable)
- `key_points_json` (text/json, default `[]`)
- `why_it_matters` (text, nullable)
- `source_kind` (`feed_excerpt` | `full_article`, nullable)
- `source_hash` (string, nullable)
- `plugin_name` (string, nullable)
- `provider` (string, nullable)
- `model_name` (string, nullable)
- `model_version` (string, nullable)
- `error_message` (string, nullable)
- `requested_by_user_id` (UUID, nullable)
- `requested_at` (timestamp, nullable)
- `completed_at` (timestamp, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Notes:

1. Latest-only persistence: regenerate overwrites prior content.
2. `source_hash` can mark summaries stale when article source content changes.

## API Surface

### Trigger Generation

1. `POST /api/v1/articles/{article_id}/summary/generate`
2. Optional request payload:
   - `force` (boolean, default `false`)
3. Behavior:
   - validates article ownership/access
   - resolves preferred source text (full article first, fallback to feed excerpt)
   - enqueues async generation job
   - returns current summary status payload

### Article Detail Extension

Extend `GET /api/v1/articles/{article_id}` with:

1. `summary` object:
   - `status`
   - `headline`
   - `key_points`
   - `why_it_matters`
   - `source_kind`
   - `source_hash`
   - `is_stale`
   - `plugin_name`
   - `provider`
   - `model_name`
   - `model_version`
   - `error_message`
   - `requested_at`
   - `completed_at`
2. `summary_capability` object:
   - `enabled` (boolean)
   - `reason` (string | null)

### Planned Plugin Contract Addition

Add planned plugin capability method:

- `summarize_article(article, options)` for on-demand structured summary generation.

## Backend Work Plan

1. Add migration + SQLAlchemy model for `article_summaries`.
2. Add summary service:
   - access validation
   - source selection policy
   - staleness/hash handling
   - enqueue and status transitions
3. Add summary job queue + worker handling (`pending` -> `succeeded`/`failed`).
4. Extend plugin manager with summary capability discovery/dispatch.
5. Add first provider plugin adapter path (initial target: Ollama Cloud).

## Frontend Work Plan

1. Add reader summary action button and pending/disabled states.
2. Add summary card in reader for structured output and status/error feedback.
3. Add generate/regenerate mutation integration.
4. Refresh/poll article detail while summary is pending.
5. Render capability-unavailable disabled hint text.

## Acceptance Criteria

1. Reader exposes `Generate summary` action for selected article.
2. Summary generation is asynchronous and status-driven.
3. Latest successful summary persists and is reused on reopen.
4. Summary input source prefers full article when available.
5. Missing plugin/config produces disabled-with-hint UX (not hidden action).
6. Feature remains optional and controlled through plugin/config enablement.

## Test Plan

Backend:

1. API tests for ownership and request validation.
2. Service tests for source selection (full article preferred fallback behavior).
3. Queue/job tests for `pending`, `succeeded`, `failed` transitions.
4. Plugin-unavailable tests for capability-disabled responses.
5. Serialization tests for extended article detail summary payload.

Frontend:

1. Reader action tests for idle/pending/success/failed states.
2. Disabled-with-hint rendering tests when capability is unavailable.
3. Summary card rendering tests for structured output fields.
4. Regression tests ensuring existing reader actions remain intact.

## Rollout Notes

1. Deliver as manual on-demand only (no auto-generate).
2. Keep capability plugin-based so it can be toggled off cleanly.
3. Keep plugin registry/config centralization as follow-up under existing planning:
   [docs/specs/plugin-configuration-registry-v1.md](plugin-configuration-registry-v1.md).

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
- Related planning: [docs/specs/plugin-configuration-registry-v1.md](plugin-configuration-registry-v1.md)
