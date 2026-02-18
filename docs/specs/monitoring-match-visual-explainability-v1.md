# Monitoring Match Visual Explainability v1 (Title + Content Match Spans)

## Status

- State: Implemented on 2026-02-18
- Scope: Delivered in backend and frontend (query-hit evidence, list/reader matched-term summaries, title/content highlighting)
- Backlog reference: [docs/backlog.md](../backlog.md)

## Context

Monitoring explainability currently includes:

1. `Why matched` textual summaries.
2. Structured evidence payloads for keyword/regex/classifier matches.
3. Reader-body highlighting with jump-to-highlight actions for offset-bearing evidence.

Current gap:

- Advanced query matches (`match_query`) are surfaced only as generic "query expression matched" without explicit
  token/phrase spans in title/content.
- Title/header does not visually highlight matched terms/spans.
- Article-list-level explainability does not surface specific matched terms in a compact way.

## Goal

Provide concrete, user-visible span-level explainability for monitoring matches so users can immediately see:

1. Which exact words/phrases matched.
2. Where they matched (`title` vs `content_text`).
3. Which matcher produced each match (`query`, `keyword`, `regex`, `classifier`).

## Non-Goals (v1)

1. No natural-language explanation generation beyond evidence-driven summaries.
2. No redesign of search query syntax.
3. No model-side semantic attribution for providers that do not return span/offset metadata.
4. No multi-color heatmap severity ranking in this version.

## User Experience (Planned)

### Article List

1. Keep existing `Matched` and `Why matched` lines.
2. Add compact matched-term summary line when evidence includes concrete hits:
   - Example: `Matched terms: darktrace (title), sentinel (content)`.
3. Cap displayed terms (for example first 3 + `+N`) to keep rows compact.

### Reader Header + Body

1. Reader title/header supports highlight markup for title-field spans.
2. Reader body keeps existing offset-first highlighting behavior.
3. Existing `Hide highlights` / `Show highlights` control remains.
4. Evidence panel groups rows by stream and matcher with field badges:
   - `title`
   - `content`

### Evidence Panel

1. Query-hit rows are first-class evidence rows (not just a generic query-matched row).
2. Each row includes:
   - matcher type
   - field
   - snippet
   - optional jump-to-highlight action when offset can map to rendered content.

## Proposed Evidence Contract Additions

Persisted in `keyword_stream_matches.match_evidence_json`.

### Rules Evidence

Add query hit structures:

- `query_hits`: list of objects:
  - `field`: `"title"` | `"content_text"`
  - `offset_basis`: `"field_text_v1"`
  - `token`: matched token/phrase
  - `clause`: optional clause id/label from parsed expression
  - `operator_context`: optional (`AND`/`OR`/`NOT`) for explainability rendering
  - `start`: integer
  - `end`: integer
  - `snippet`: string

Notes:

1. Existing `query: { expression: true }` can remain for backwards compatibility.
2. `query_hits` should be present only when precise hit extraction is possible.

### Classifier Evidence

No contract break required; continue using `findings` with optional:

- `field`
- `start`
- `end`
- `offset_basis`

## Backend Work Plan (Planned)

1. Extend query evaluation path to capture matched tokens/phrases with offsets for successful expressions.
2. Add query-hit extraction helpers compatible with:
   - quoted phrases
   - wildcard suffix terms
   - fuzzy tokens
3. Persist `query_hits` in match evidence during:
   - ingest-time matching
   - stream backfill matching
4. Keep existing evidence keys stable for compatibility with current frontend.

## Frontend Work Plan (Planned)

1. Extend evidence model parsing in `ReaderPane` for `query_hits`.
2. Render title-field highlights in reader title.
3. Render query-hit evidence rows with snippets and jump controls when supported.
4. Extend article-list row metadata with compact matched-term summary.
5. Preserve resilience behavior when evidence payloads are malformed/missing.

## API Surface Impact

No new endpoint required in v1.

Existing outputs already carry `stream_match_evidence` payloads:

1. `GET /api/v1/articles`
2. `GET /api/v1/articles/{article_id}`
3. `GET /api/v1/streams/{stream_id}/articles`

## Acceptance Criteria (for later implementation)

1. Successful query matches produce concrete `query_hits` in persisted evidence when offsets are derivable.
2. Reader highlights matching spans in both title and body where evidence provides offsets.
3. Evidence panel renders query-hit rows with field/snippet context.
4. Article list shows compact matched-term summary for evidence-bearing matches.
5. Existing matcher evidence rendering remains backward compatible.

## Test Plan (for later implementation)

Backend:

1. Unit tests for query-hit extraction across phrase/wildcard/fuzzy cases.
2. Stream service tests verifying `query_hits` persistence for ingest and backfill.
3. Regression tests for existing keyword/regex/classifier evidence payloads.

Frontend:

1. Reader tests for title and body highlighting from `query_hits`.
2. Evidence panel tests for query-hit row rendering and jump behavior.
3. Article-list tests for compact matched-term summary line behavior.

## Phased Delivery Plan

1. Phase 1:
   - backend `query_hits` persistence
   - reader evidence panel rendering for query hits
2. Phase 2:
   - title highlighting support
   - article-list matched-term summary
3. Phase 3:
   - UI polish and density tuning
   - a11y pass and keyboard/focus refinements

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
