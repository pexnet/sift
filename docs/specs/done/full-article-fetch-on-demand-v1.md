# Full Article Fetch On-Demand v1

## Status

- State: Completed (2026-02-22)
- Scope: Implemented in backend + frontend
- Backlog reference: [docs/backlog.md](../../backlog.md)

## Implementation Summary

Backend:

1. Added `article_fulltexts` persistence model + migration.
2. Added fulltext fetch service with URL safety checks and bounded extraction flow.
3. Added `POST /api/v1/articles/{article_id}/fulltext/fetch`.
4. Extended article detail payload with fulltext status/content fields and `content_source`.

Frontend:

1. Added reader `Fetch full article` / `Refetch full article` action with pending/error handling.
2. Wired fulltext fetch mutation and article-detail refresh behavior.
3. Reader now renders full extracted content when available and shows source label
   (`Source: full article` / `Source: feed excerpt`).

Verification:

- Backend:
  - `python -m pytest tests/test_article_fulltext_service.py tests/test_article_fulltext_api.py`
  - `python -m ruff check src/sift/api/routes/articles.py src/sift/services/article_fulltext_service.py src/sift/services/article_service.py src/sift/db/models.py src/sift/domain/schemas.py tests/test_article_fulltext_service.py tests/test_article_fulltext_api.py`
  - `python -m mypy src/sift/services/article_fulltext_service.py src/sift/services/article_service.py src/sift/api/routes/articles.py src/sift/domain/schemas.py --no-incremental`
- Frontend:
  - `npm --prefix frontend run test -- src/features/workspace/components/ReaderPane.test.tsx src/features/workspace/routes/WorkspacePage.test.tsx src/entities/article/model.test.ts`
  - `npm --prefix frontend run typecheck`
  - `npm --prefix frontend run lint`

## Context

Current reader behavior renders article content from feed payload (`articles.content_text`) and exposes `Open original`
for the source page. Many feeds publish truncated summaries rather than full content.

This creates a gap for reader-first workflows where users want to stay in Sift and fetch a cleaner full-article body
without leaving the app.

## Goal

Provide a user-triggered `Fetch full article` action in the reader that:

1. fetches the source page for the selected article,
2. extracts main readable content,
3. stores the extracted result for reuse,
4. renders full content in reader when available.

## Non-Goals (v1)

1. No automatic full-content fetching for every ingested article.
2. No paywall bypass or authenticated-site scraping.
3. No JavaScript browser rendering pipeline (headless browser is out of scope for v1).
4. No cross-user personalization of extracted fulltext.

## User Experience (Planned)

### Reader Action

1. Add `Fetch full article` button in reader actions.
2. If fulltext already exists, action label changes to `Refetch full article`.
3. While running, action shows pending state (`Fetching...`) and is disabled.

### Reader Content Behavior

1. If fulltext fetch succeeds, reader renders extracted full content.
2. If no fulltext exists, reader continues rendering feed-provided content.
3. Surface a lightweight content-source label:
   - `Source: full article`
   - `Source: feed excerpt`

### Error Handling

1. If fetch/extraction fails, show concise error feedback and keep existing feed excerpt.
2. Allow retry from same action.

## Proposed Data Model

Add new table: `article_fulltexts` (1:1 with `articles`).

Proposed fields:

- `id` (UUID, primary key)
- `article_id` (UUID, unique FK -> `articles.id`, indexed)
- `status` (`idle` | `pending` | `succeeded` | `failed`, indexed)
- `source_url` (string, nullable)
- `final_url` (string, nullable)
- `content_text` (text, nullable)
- `content_html` (text, nullable)
- `extractor` (string, nullable)  # provider/library identifier
- `error_message` (string, nullable)
- `fetched_at` (timestamp, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Notes:

1. Keep extracted content separate from feed-ingested `articles.content_text`.
2. Retain latest successful fetch only in v1 (history/versioning deferred).

## Proposed API Surface

1. Trigger fetch:
   - `POST /api/v1/articles/{article_id}/fulltext/fetch`
   - behavior:
     - validates article ownership access
     - enqueues/executes fulltext fetch flow
     - returns current status payload
2. Read status/content:
   - extend existing `GET /api/v1/articles/{article_id}` with:
     - `fulltext_status`
     - `fulltext_error`
     - `fulltext_fetched_at`
     - `fulltext_content_text`
     - `fulltext_content_html`
     - `content_source` (`feed_excerpt` | `full_article`)

## Backend Work Plan (Planned)

1. Add migration + SQLAlchemy model for `article_fulltexts`.
2. Add fulltext service:
   - validate canonical/source URL
   - fetch page via `httpx`
   - extract readable content using selected extractor
   - persist status/content/error
3. Add API endpoint `POST /fulltext/fetch`.
4. Extend article detail serialization to include fulltext fields.
5. Add SSRF and safety guards:
   - allowlist schemes (`http`, `https`)
   - block loopback/private network targets
   - bounded timeout/body size limits

## Frontend Work Plan (Planned)

1. Add reader action button and pending/error states.
2. Call fulltext fetch endpoint on click.
3. Refresh article detail and render fulltext when available.
4. Show content-source label (`full article` vs `feed excerpt`).
5. Preserve existing `Open original` behavior.

## Acceptance Criteria

1. User can trigger full-article fetch from reader with one click.
2. Successful extraction persists and is shown on subsequent opens.
3. Failures do not replace existing feed excerpt content.
4. Access controls match current article ownership boundaries.
5. Reader remains usable even when extraction fails.

## Test Plan (for later implementation)

Backend:

1. Service tests for fetch success, extraction failure, and unsupported URL cases.
2. API tests for auth/ownership boundaries and status transitions.
3. SSRF guard tests (private/loopback disallowed).

Frontend:

1. Reader action tests for idle/pending/success/failure states.
2. Rendering tests for content source switching.
3. Regression tests for existing reader actions and keyboard shortcuts.

## Rollout Notes

1. Start as explicit on-demand action only.
2. If extraction quality is acceptable, evaluate optional auto-fetch policies in a later phase.
3. Keep extractor abstraction pluggable to allow provider changes without API contract breakage.

## Backlog References

- Product backlog: [docs/backlog.md](../backlog.md)
