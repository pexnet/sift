# Session Notes

## 2026-02-17 (Planning Update: Monitoring Span Explainability + Action Iconification)

### Implemented This Session

- Added detailed planning spec for monitoring match visual explainability:
  - `docs/specs/monitoring-match-visual-explainability-v1.md`
  - scopes title/content span-level visibility for query/rule/classifier evidence
  - defines proposed `query_hits` evidence contract extension and phased implementation plan
- Added detailed planning spec for workspace action iconification:
  - `docs/specs/workspace-action-iconification-v1.md`
  - scopes icon-first list/reader action controls with tooltips and explicit accessibility labels
- Updated backlog next-iteration actions:
  - added both slices under `Next UI Slice` planned actions in `docs/backlog.md`
  - linked both new specs in backlog linked-spec references
  - clarified deferred monitoring v2 note to reference new next-iteration span explainability scope

### Verification

- Documentation-only planning update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Monitoring Explainability: Rich Classifier Findings)

### Implemented This Session

- Extended classifier plugin decision contract with structured findings:
  - `StreamClassificationDecision.findings` now accepts a list of finding objects.
- Upgraded built-in classifier plugin evidence output:
  - keyword heuristic classifier now emits finding rows with label/snippet/score
  - when available, findings include field offsets for UI highlight mapping
- Extended stream matching evidence persistence:
  - classifier evidence now stores normalized `findings` blocks
  - classifier reason fallback now uses first finding summary when explicit reason is absent
  - classifier snippets are derived from findings for backward-compatible rendering
- Upgraded reader explainability rendering:
  - match evidence summary now includes classifier finding counts and first finding details
  - evidence panel now renders classifier findings as first-class rows
  - findings with `field=content_text` + offsets support jump-to-highlight actions
- Added/updated tests:
  - `tests/test_stream_service.py` (classifier finding evidence assertions)
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx` (classifier findings summary + evidence row rendering)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

## 2026-02-17 (Classifier Run Persistence + Model/Version Tracking Baseline)

### Implemented This Session

- Added classifier run persistence model and migration:
  - migration: `alembic/versions/20260217_0013_stream_classifier_runs.py`
  - model: `stream_classifier_runs` in `src/sift/db/models.py`
- Extended classifier plugin decision contract with tracking metadata:
  - `provider`, `model_name`, `model_version` in `StreamClassificationDecision`
  - built-in keyword heuristic classifier now emits baseline model metadata
- Extended stream matching execution path:
  - stream service now captures classifier run decisions (match status, confidence, threshold, duration, metadata)
  - ingest flow persists classifier runs for classifier-enabled streams
  - stream backfill flow persists classifier runs for classifier-enabled streams
- Added stream diagnostics API endpoint:
  - `GET /api/v1/streams/{stream_id}/classifier-runs`
  - returns recent classifier runs for the user-owned stream
- Added/updated tests:
  - `tests/test_stream_service.py` (classifier run capture + persistence coverage)
  - `tests/test_stream_classifier_runs_api.py` (new endpoint coverage)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_stream_classifier_runs_api.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`

## 2026-02-17 (Planning Update: Silent Feeds for Monitoring-Only Population)

### Implemented This Session

- Added new planning spec: `docs/specs/silent-feeds-v1.md`.
- Scoped `silent` feed mode semantics:
  - silent feeds keep normal ingestion and monitoring stream matching behavior
  - new ingested articles from silent feeds are auto-marked read
  - switching a feed to silent bulk-marks existing unread for that feed as read
  - unsilencing stops future auto-read but does not revert historical read states
- Updated planning docs for backlog/architecture alignment:
  - added linked spec and deferred backlog item (placed as lowest priority) in `docs/backlog.md`
  - added deferred architecture section for silent feed model/API/pipeline implications in `docs/architecture.md`

### Verification

- Documentation-only planning update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Planning Update: Discovery Providers + Free-Tier Rate Limits)

### Implemented This Session

- Extended `Discover feeds v1` planning spec with provider strategy details:
  - default provider chain guidance (`searxng` primary + managed fallback)
  - optional adapter notes for constrained/legacy providers
- Added planned discovery execution flow:
  - query variant compilation
  - provider search execution
  - staged feed endpoint resolution (direct parse, HTML autodiscovery, constrained heuristics)
  - validation, dedupe, and source attribution behavior
- Added explicit free-tier protection planning:
  - per-provider budget/rate-limit controls (`max_requests_per_run`, `max_requests_per_day`, request spacing, and
    query/result caps)
  - partial-result warning behavior when budget exhaustion occurs
- Updated related planning docs for consistency:
  - `docs/specs/plugin-configuration-registry-v1.md`
  - `docs/architecture.md`
  - `docs/backlog.md`

### Verification

- Documentation-only planning update.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update.

## 2026-02-17 (Planning Alignment: Discover Feeds + Discovery Streams)

### Implemented This Session

- Updated planning/docs direction from saved-driven recommendations to stream-driven discovery:
  - locked user-facing naming: `Discover feeds` + `Discovery streams`
  - locked v1 model as separate discovery domain (not monitoring stream reuse)
- Captured discovery architecture decisions across docs:
  - separate `discovery_streams` from monitoring `keyword_streams`
  - per-stream manual generation workflow
  - recommendation dedupe by normalized URL with source-stream attribution
- Captured recommendation decision semantics for v1:
  - statuses include `pending`, `accepted`, `denied`, `resolved_existing`
  - denied URLs are suppressed until manual reset
  - already subscribed feed URLs are auto-resolved as `resolved_existing`
- Captured product/UX boundary:
  - optional copy-from-monitoring convenience into discovery stream criteria
  - no saved/starred article seed usage in v1
- Updated linked specs and plugin naming examples to use `Discover feeds` / `discover_feeds`.

### Verification

- Documentation-only alignment pass.
- No backend/frontend runtime behavior changes were implemented in this session.
- No code test suite execution was required for this docs-only update (optional markdown checks may be run separately).

## 2026-02-16 (Workspace UX: Help in Rail + Scope-Aware Mark Read)

### Implemented This Session

- Added Help entry directly in the left workspace rail (`/app`) for fast discoverability.
- Added backend scope-aware read action endpoint:
  - `POST /api/v1/articles/state/mark-scope-read`
  - marks all matching articles as read based on current scope/state/query filters
- Added service method `mark_scope_as_read(...)` in article service to evaluate full scope filters (including advanced query syntax) before bulk state update.
- Updated workspace list action copy and behavior:
  - button now reads `Mark all in scope as read`
  - action prompts user confirmation before execution
  - no longer limited to currently visible rows
- Added/updated tests:
  - `tests/test_article_service.py`
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/hooks/useWorkspaceShortcuts.test.tsx`

### Verification

- `python -m pytest tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src --no-incremental`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx src/features/workspace/hooks/useWorkspaceShortcuts.test.tsx`

## 2026-02-16 (Help Page: Monitoring Setup + Search Syntax Reference)

### Implemented This Session

- Added authenticated help route: `/help`.
- Added new help page UI focused on:
  - configuring monitoring feeds step-by-step
  - search query syntax (`AND`, `OR`, `NOT`, grouping, quotes, wildcard, fuzzy)
  - regex/include/exclude behavior guidance
- Added help entry links:
  - from settings (`/account`)
  - from monitoring feed management (`/account/monitoring`)
- Added frontend tests:
  - `frontend/src/features/help/routes/HelpPage.test.tsx`
  - updated `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - updated `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/help/routes/HelpPage.test.tsx src/features/auth/routes/AccountPage.test.tsx src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

## 2026-02-16 (Workspace UI Touch-Up: Mark All Read + Remove Stale Magic Copy)

### Implemented This Session

- Added bulk article state wiring in frontend API/hooks:
  - `bulkPatchArticleState` client call to `POST /api/v1/articles/state/bulk`
  - `useBulkPatchArticleStateMutation` for workspace usage
- Added `Mark all as read` action in article list pane:
  - action targets unread articles currently loaded in the list
  - disabled when there are no unread items or mutation is in progress
- Removed stale “Magic sorting” banner copy from article list pane because that feature text was not aligned with current UI behavior.
- Updated article list pane tests for the new bulk action behavior.

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx`

### Notes

- Current list fetch is capped to the active list window (default 50), so `Mark all as read` applies to unread articles currently loaded in the pane.

## 2026-02-16 (Monitoring Management v2: Offset-Aware Highlighting + Evidence Panel)

### Implemented This Session

- Extended stream evidence payloads with explicit offset metadata marker:
  - rule hits now include `offset_basis: field_text_v1`
- Extended classifier evidence payloads with snippet-ready structure:
  - classifier reason now also emits `snippets: [{ text: ... }]`
- Upgraded reader highlighting from term-only to offset-aware rendering:
  - uses `field=content_text` + `start/end` offsets to apply precise `<mark>` ranges in reader body
  - preserves term-based fallback when offset mapping cannot be applied
- Added reader evidence panel with per-stream details:
  - keyword/regex hit rows with snippets
  - classifier rows/snippets
  - `Jump to highlight` actions for rows mapped to rendered highlight anchors
- Updated UI styling for evidence panel and highlight affordances.
- Added frontend test coverage for evidence jump behavior and maintained highlight toggle coverage.

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `python -m ruff check src tests`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

### Notes

- Offset mapping is now primary for body highlighting; fallback term highlighting remains in place for resilience.
- Remaining explainability follow-up is exposing richer plugin finding structures from plugin implementations (beyond classifier reason snippets).

## 2026-02-16 (Monitoring Management v2: Reader Inline Match Highlighting)

### Implemented This Session

- Added inline reader-body highlighting for monitoring match evidence terms.
- Highlight extraction now uses structured match evidence values (keyword and regex matched values).
- Added reader action toggle:
  - `Hide highlights` / `Show highlights`
  - toggle is shown when match evidence terms are available for the selected article
- Added highlight styling token/class:
  - `.workspace-reader__highlight`
- Added frontend coverage for highlight rendering and toggle behavior:
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

### Notes

- Highlighting is DOM-based and preserves existing sanitized reader markup.
- This is an iteration-1 implementation focused on evidence values; future refinement can add precise offset-aware highlighting.

## 2026-02-16 (Monitoring Management v2: Structured Match Evidence + Reader Details)

### Implemented This Session

- Added persisted structured evidence payload for stream matches:
  - migration: `alembic/versions/20260216_0012_stream_match_evidence.py`
  - model field: `keyword_stream_matches.match_evidence_json`
- Extended stream matching to produce structured rule/classifier evidence:
  - keyword and regex hit records now include field, offsets, and snippets
  - classifier matches now capture plugin, confidence/threshold, and reason
  - hybrid mode now stores combined rules/classifier evidence payloads
- Extended backend API outputs with evidence:
  - `StreamArticleOut.match_evidence`
  - `ArticleListItemOut.stream_match_evidence`
  - `ArticleDetailOut.stream_match_evidence`
- Extended article service stream mapping to parse and return per-stream evidence payloads.
- Updated reader explainability rendering:
  - preserved `Why matched` textual reason summaries
  - added `Match evidence` summaries with keyword/regex snippet context and classifier details
- Added/updated tests:
  - `tests/test_stream_service.py`
  - `tests/test_stream_backfill_api.py`
  - `tests/test_article_service.py`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ReaderPane.test.tsx`

### Notes

- Monitoring explainability now persists machine-readable evidence suitable for future UI highlight rendering.
- Remaining monitoring v2 enhancement area is article-content level inline highlighting (actual span markup), not just textual evidence summaries.

## 2026-02-16 (Monitoring Management v2: Plugin Matcher Config Baseline)

### Implemented This Session

- Added persisted classifier config for monitoring streams:
  - migration: `alembic/versions/20260216_0011_stream_classifier_config.py`
  - model field: `keyword_streams.classifier_config_json`
- Extended stream schemas with `classifier_config` for create/update/out payloads.
- Added backend classifier config validation in stream service:
  - must be a JSON object
  - must be JSON-serializable
  - bounded payload size (max 5000 chars serialized)
- Extended classifier execution context (`StreamClassifierContext`) to include `classifier_config`.
- Updated built-in heuristic classifier plugin to honor optional config flags:
  - `require_all_include_keywords`
  - `min_keyword_ratio`
- Updated monitoring UI to edit classifier config JSON and validate JSON pre-submit.
- Updated tests:
  - `tests/test_stream_service.py` (config persistence and classifier-context usage)
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx` (config payload wiring)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Notes

- This completes plugin matcher config wiring for monitoring v2.
- Remaining v2 scope is deeper explainability rendering (matched spans/snippets).

## 2026-02-16 (Monitoring Management v2: Explainability Baseline)

### Implemented This Session

- Added persisted match-reason evidence for monitoring stream matches:
  - migration: `alembic/versions/20260216_0010_stream_match_reason.py`
  - model field: `keyword_stream_matches.match_reason`
- Extended stream matching flow to produce reason summaries for matches:
  - query/keyword/regex/source/language/classifier reasons
  - ingestion and backfill now persist match reasons per stream/article match row
- Extended article APIs to return stream match reason mappings:
  - `ArticleListItemOut.stream_match_reasons`
  - `ArticleDetailOut.stream_match_reasons`
- Extended stream article payloads with `match_reason` in `StreamArticleOut`.
- Updated workspace explainability rendering:
  - article rows render `Why matched` summaries when reason evidence exists
  - reader pane renders per-stream reason summaries
- Added/updated tests:
  - `tests/test_stream_service.py`
  - `tests/test_stream_backfill_api.py`
  - `tests/test_article_service.py`
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- src/features/workspace/components/ArticlesPane.test.tsx src/features/workspace/components/ReaderPane.test.tsx src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Notes

- This completes a textual explainability baseline for monitoring matches.
- Remaining v2 explainability scope is keyword/regex span highlighting and plugin snippet rendering.

## 2026-02-16 (Monitoring Management v2: Regex Matcher Baseline)

### Implemented This Session

- Added regex matcher fields for monitoring streams:
  - migration: `alembic/versions/20260216_0009_stream_regex_fields.py`
  - persisted columns: `keyword_streams.include_regex_json`, `keyword_streams.exclude_regex_json`
- Extended stream schemas and stream CRUD payloads with regex rule lists (`include_regex`, `exclude_regex`).
- Extended stream matching engine:
  - include regex rules require at least one regex hit in article title/content
  - exclude regex rules reject article matches when regex patterns hit title/content
  - regex patterns are validated on stream create/update with explicit validation errors for invalid patterns
- Updated monitoring UI editor to support include/exclude regex rules and persist them via stream APIs.
- Updated monitoring stream cards to display configured regex rules.
- Added/updated tests:
  - `tests/test_stream_service.py` (regex matching and regex validation coverage)
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx` (regex payload wiring)

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `pnpm --dir frontend run test -- src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`

### Notes

- Monitoring management v2 now has:
  - historical backfill execution baseline
  - regex matcher expansion baseline
- Remaining v2 scope is plugin matcher expansion and richer explainability rendering.

## 2026-02-16 (Monitoring Management v2 Baseline: Backfill Execution)

### Implemented This Session

- Added backend stream backfill endpoint: `POST /api/v1/streams/{stream_id}/backfill`.
- Added stream backfill service flow:
  - scan existing user-owned articles
  - recompute stream match membership using current stream rules/query/classifier mode
  - replace stale `keyword_stream_matches` rows for the stream with recomputed results
  - return execution counts (`scanned_count`, `previous_match_count`, `matched_count`)
- Added API coverage: `tests/test_stream_backfill_api.py`.
- Added service coverage for replacement behavior: `tests/test_stream_service.py`.
- Updated monitoring UI backfill feedback:
  - success message now shows concrete counts (`matched` vs `scanned`)
  - existing explicit unavailable-state handling for legacy/non-upgraded backends is preserved
- Updated frontend typing/API client for backfill response payload shape.

### Verification

- `python -m pytest tests/test_stream_service.py tests/test_stream_backfill_api.py`
- `pnpm --dir frontend run test -- src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`
- `python -m ruff check src tests`
- `python -m mypy src`

### Notes

- This completes the historical backfill execution baseline for monitoring management v2.
- Remaining v2 scope is regex/plugin matcher expansion and richer explainability rendering.

## 2026-02-16 (Monitoring Search Language v1 Slice Implemented)

### Implemented This Session

- Added backend monitoring/article search language module: `src/sift/search/query_language.py`.
- Added query-language syntax support:
  - boolean operators: `AND`, `OR`, `NOT` (case-insensitive)
  - grouping with parentheses
  - quoted phrases
  - suffix wildcard (`term*`)
  - fuzzy tokens (`term~1`, `term~2`)
- Added stream persistence for query expressions:
  - migration: `alembic/versions/20260216_0008_stream_match_query.py`
  - model/schema support for `keyword_streams.match_query`
- Integrated query parsing/validation into stream create/update and ingest-time stream matching.
- Integrated advanced query handling in article listing search with clear 400-level validation failures for invalid syntax.
- Added monitoring UI support for editing `Search query (v1)` in `/account/monitoring`.
- Added/updated tests:
  - `tests/test_query_language.py`
  - `tests/test_stream_service.py`
  - `tests/test_article_service.py`
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

### Verification

- `python -m pytest tests/test_query_language.py tests/test_stream_service.py tests/test_article_service.py`
- `python -m ruff check src tests`
- `python -m mypy src`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- --run`
- `pnpm --dir frontend run build`

### Notes

- PostgreSQL acceleration for advanced query filtering is intentionally deferred to a follow-up optimization slice.

## 2026-02-16 (Planning: Monitoring Search Language v1 Sketched)

### Planning Update

- Added a new prioritized backlog item for a monitoring search language v1 using boolean operators.
- Captured initial syntax/behavior sketch in `docs/backlog.md`:
  - operators: `AND`, `OR`, `NOT`
  - grouping with parentheses
  - quoted phrase support
  - operator precedence (`NOT` > `AND` > `OR`)
- Captured implementation outline:
  - backend parser/validator + clear syntax errors
  - expression persistence on monitoring definitions
  - ingest-time evaluation for stream matching
  - monitoring UI editor input + validation feedback
- Marked advanced matcher composition (regex/plugin combinations) as deferred v2 scope.

## 2026-02-16 (Monitoring Feed Management v1 Slice Implemented)

### Implemented This Session

- Added stream-backed monitoring management route: `/account/monitoring`.
- Added monitoring management frontend data layer:
  - stream API client module (`GET/POST/PATCH/DELETE /api/v1/streams`)
  - optional backfill trigger entry point (`POST /api/v1/streams/{stream_id}/backfill`) with explicit unavailable-state UX
  - React Query hooks for list/create/update/delete/backfill operations
- Added settings entry point:
  - `Manage monitoring feeds` action on `/account`
- Added monitoring management UX:
  - create/edit/delete/toggle-active monitoring definitions
  - classifier mode/plugin/confidence controls
  - keyword/source/language criteria editing
  - user feedback banners for success/error/info outcomes
- Added explainability affordances in workspace:
  - article list rows show matched monitoring stream labels
  - reader header shows matched monitoring stream labels
- Added and updated tests:
  - `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`
  - `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - `frontend/src/features/workspace/components/ArticlesPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- --run`
- `pnpm --dir frontend run build`

## 2026-02-16 (Backlog Source-of-Truth Consolidation)

### Implemented This Session

- Added `docs/backlog.md` as the canonical backlog source of truth.
- Consolidated backlog state into explicit status buckets:
  - `Done` (historical completed work)
  - `Next` (current prioritized items)
  - `Deferred` (future backlog)
- Added references in `AGENTS.md` so future sessions read/update `docs/backlog.md` during planning.

### Notes

- Detailed long-term backlog content was migrated from this file to `docs/backlog.md` to avoid drift.

## 2026-02-16 (Project/UI Plan Review + Monitoring Management Prioritized)

### Planning Review (UI)

- Confirmed completed UI improvements in the current plan:
  - reader-first `/app` shell with 3-pane responsive behavior
  - folder/feed navigation IA and folder management flows
  - topbar quick theme toggle + settings entry point
  - unified `/account` settings hub (`themeMode`, `themePreset`, `density`, `navPreset`)
  - preset-aware theming across rail/nav/list/reader (light + dark)
  - settings accessibility hardening (group semantics, keyboard support, focus-visible states)
  - reset-to-defaults action and settings route test coverage
  - monitoring section placement/expand-collapse behavior in navigation

### Priority Update

- Promoted monitoring feed definition management to the next prioritized UI slice.
- Kept the core platform sequence unchanged:
  1. stream-level ranking/prioritization
  2. classifier run persistence/model tracking
  3. vector-database plugin integration
  4. scheduler/ingestion observability

### Next Step (UI Slice Scope)

1. Define route + information architecture for monitoring definition CRUD.
2. Add explainability affordances in list/reader for match reasons.
3. Add optional historical backfill trigger in the management flow.

## 2026-02-16 (Theme Consistency Follow-Up + Planning Alignment)

### Implemented This Session

- Completed final preset consistency follow-up for remaining non-themed surfaces:
  - expanded preset-specific base surface tokens (`bg`, `surface`, `surface-soft`, `surface-muted`, `text`, `muted`, `border`)
  - aligned MUI palette per preset/mode (`background`, `text`, `divider`, and `action` tokens) so controls match pane theme
- Aligned planning docs (`AGENTS.md`, `docs/architecture.md`) to remove stale deferred UI-polish items that are now complete.
- Set the next UI-focused deferred slice explicitly to monitoring feed definition management UX/API.

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test -- --run`
- `pnpm --dir frontend run build`

### Next Step (UI)

1. Start monitoring feed definition management slice:
   - define route + IA for monitoring definition CRUD
   - add explainability affordances in list/reader for why an article matched
   - wire optional backfill trigger entry point in the management flow

## 2026-02-16 (UI Extensions Completed: Preset Consistency + Contrast + Settings UX)

### Implemented This Session

- Completed the planned UI extension pass across workspace and settings:
  1. Visual consistency per preset
     - expanded preset-aware visual tokens across workspace panes (rail/nav/list/reader)
     - unified topbar/nav/list/reader surface tints using accent-aware tokenized gradients
  2. Contrast/interaction tuning per preset
     - improved preset-sensitive hover/selected interaction states and rail action states
     - moved focus ring to accent-derived token so each preset has coherent focus color behavior
     - tuned interaction/background tokens for both light and dark preset variants
  3. Settings UX accessibility/responsive polish
     - added `Reset to defaults` action for UI preferences
     - strengthened grouped settings semantics and keyboard operation support (arrows + home/end)
     - improved mobile behavior for settings controls (full-width reset and toggle layout)

- Added/expanded settings route tests:
  - `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - validates accessible settings structure, persistence, reset behavior, and keyboard navigation

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

## 2026-02-16 (UI Polish + Settings Accessibility + Route Tests)

### Implemented This Session

- Completed preset-by-preset interaction polish across workspace surfaces:
  - introduced semantic interaction tokens for hover/selected states, list banners, reader callouts/code blocks
  - made rail gradient and rail interaction states preset-aware (Classic/Ocean/Graphite/Sand in light+dark)
  - removed stale navigation-preset toolbar CSS that is no longer used
- Improved settings accessibility and keyboard behavior on `/account`:
  - upgraded settings controls to semantic `fieldset`/`legend` groups
  - added helper text for keyboard operation
  - implemented arrow/home/end keyboard selection handling for toggle groups
  - improved focus-visible and selected-state styling for settings toggle controls
- Added targeted settings route tests for interaction and persistence:
  - `frontend/src/features/auth/routes/AccountPage.test.tsx`
  - validates accessible settings sections/labels
  - validates persisted unified preferences and legacy key synchronization
  - validates keyboard arrow selection behavior for theme mode group

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

## 2026-02-16 (UI Settings Hub Slice Implemented)

### Implemented This Session

- Implemented unified frontend UI preferences model in `frontend/src/app/uiPreferences.ts`:
  - persisted model: `themeMode`, `themePreset`, `density`, `navPreset`
  - migration-friendly read path from legacy keys
  - synchronized writes to unified + legacy keys for backward compatibility
- Updated app providers and theme wiring:
  - `AppProviders` now stores and exposes unified UI preferences state
  - theme factory now supports `(themeMode, themePreset)`
  - document theme attributes now include both mode and preset
- Expanded `/account` into a settings hub:
  - Appearance controls: theme mode + theme preset
  - Reading/Layout controls: density + nav preset
  - Account section retains identity summary
- Removed duplicate inline display controls from workspace navigation:
  - nav preset selection removed from `NavigationPane`
  - navigation visual preset now flows from app settings state
- Added curated preset token variants in CSS for light/dark presentation tuning:
  - Sift Classic, Ocean Slate, Graphite Violet, Warm Sand
- Added/updated frontend tests:
  - `frontend/src/app/uiPreferences.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Verification

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

## 2026-02-16 (Reprioritization Update)

### Priority Update

- Reprioritized active work to make the UI settings-hub vertical slice priority #1.
- Updated `AGENTS.md`, `docs/architecture.md`, and `docs/session-notes.md` to use the same ordering.
- Kept OIDC deferred and reframed deferred UI work to post-foundation preset/polish expansion.

## 2026-02-16

### Planning Alignment Audit

- Aligned planning language across `AGENTS.md`, `docs/architecture.md`, and `docs/session-notes.md`.
- Confirmed one canonical current core priority sequence:
  1. stream-level ranking/prioritization
  2. classifier run persistence/model tracking
  3. vector-database plugin integration
  4. scheduler/ingestion observability
- Validated runtime baseline stabilization items as complete:
  - scheduler job-id delimiter compatibility (`ingest-<feed_id>`, legacy `ingest:<feed_id>` lookup)
  - dev seed idempotent behavior for feeds/folders/monitoring streams
- Moved OIDC planning consistently into deferred scope.
- Frontend settings/theme sprint planning from this audit is superseded by the reprioritization update above.

### Verification

- Cross-doc planning sections checked via ripgrep for:
  - `Next Delivery Sequence`
  - `Current Priority Plan`
  - `Planned Next Moves`
  - `Deferred Delivery Sequence`
  - `Next UI Sprint`
- Runtime baseline checks:
  - `python -m pytest tests/test_scheduler.py tests/test_dev_seed_service.py`

## 2026-02-15

### Architecture Baseline (Current)

- Backend is API-only FastAPI (`/api/v1/*`) and does not serve frontend pages or static bundles.
- Frontend is a standalone React + TypeScript app in `frontend/`.
- Frontend routes (`/app`, `/login`, `/register`, `/account`) are owned by the SPA runtime.
- Frontend/backend integration is API-only via REST endpoints.

### Implemented This Session

- Removed backend web delivery package and route surface (`src/sift/web/*`).
- Added CORS configuration in backend settings and middleware wiring in `src/sift/main.py`.
- Added API-only regression test: `tests/test_api_only_surface.py`.
- Set frontend build output to `frontend/dist`.
- Added frontend API base URL support through `VITE_API_BASE_URL`.
- Standardized docs (`AGENTS.md`, architecture, getting-started, development, deployment) to the API-only + standalone SPA model.
- Updated Dev Container stack to include frontend service and default port `5173`.
- Updated root `docker-compose.yml` to start full local stack including frontend dev server (`http://localhost:5173`).

### Verification

- Frontend:
  - `pnpm --dir frontend run gen:openapi`
  - `pnpm --dir frontend run lint`
  - `pnpm --dir frontend run typecheck`
  - `pnpm --dir frontend run test`
  - `pnpm --dir frontend run build`
- Backend:
  - `python -m ruff check src tests`
  - `python -m mypy src`
  - `python -m pytest`

### Current Priority Plan

1. Add stream-level ranking and prioritization controls.
2. Add classifier run persistence and model/version tracking.
3. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
4. Add scheduler and ingestion observability (metrics, latency, failures) after core content features.

### Deferred

1. External OIDC provider integration (Google first, then Azure/Apple).
2. UI preset/consistency extension work completed on 2026-02-16; next deferred UI slice is monitoring feed
   definition management.

### Workspace UI Slice: Folder + Reader v1

- Refactored `/app` to a light, compact reader-first shell:
  - fixed app rail
  - hierarchical navigation pane
  - compact article list
  - persistent reader pane
- Removed dashboard cards from the `/app` workspace route.
- Added hierarchical navigation view model mapping in `frontend/src/entities/navigation/model.ts`:
  - system, folder, feed, and stream scope mapping
  - unified scope label resolution for current URL scope
- Added folder management and feed assignment flows using existing APIs:
  - create/rename/delete folder
  - move feed to folder / unfiled
  - query invalidation for navigation, folders, feeds, and articles
- Reworked article list rows for compact dense rendering with unread/saved indicators and metadata.
- Reworked reader pane with core actions (`read`, `save`, `open original`, `prev`, `next`).
- Added responsive behavior updates:
  - desktop: fixed 3-pane layout
  - tablet/mobile: collapsible navigation drawer from rail action
  - mobile: progressive list/reader panel flow with back-to-list action
- Added/updated frontend tests:
  - navigation hierarchy mapping
  - folder DTO/validation shaping
  - compact article row rendering
  - reader action wiring

### Verification (Workspace Slice)

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`
- `python -m pytest tests/test_article_state_api.py tests/test_article_service.py`

### Workspace UI Modernization + Reader Formatting

- Implemented editorial-light workspace polish for `/app`:
  - updated visual tokens and spacing hierarchy for rail/nav/list/reader panes
  - improved hover/active/focus states and compact readability
  - replaced rail glyph labels with MUI icons for clearer affordances
- Implemented safe reader content rendering:
  - added `frontend/src/features/workspace/lib/readerContent.ts`
  - sanitized article markup using DOMPurify with allowlisted semantic tags
  - normalized rendered links with safe `target`/`rel` attributes
  - converted plaintext payloads into paragraph-based HTML fallback
- Updated reader component contract:
  - `ReaderPane` now renders preprocessed sanitized HTML body content
  - kept existing reader action behavior (`read/save/open/prev/next`)
- Added tests for sanitizer and reader behavior:
  - `frontend/src/features/workspace/lib/readerContent.test.ts`
  - expanded `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Workspace Nav/Visual Polish v2

- Implemented reliable folder interaction split in navigation:
  - row click now selects folder scope only
  - chevron click toggles expansion only (single-click behavior)
- Added folder controls:
  - `Expand all`
  - `Collapse all`
  - folder expansion state persisted in localStorage (`NAV_FOLDERS_EXPANDED_KEY`)
- Added feed icons in folder/feed tree:
  - favicon URL derived from feed `site_url` or `url`
  - graceful fallback to deterministic initial avatar if favicon load fails
- Applied softer visual tuning in workspace styles:
  - lower-contrast borders/backgrounds
  - calmer selected/hover states
  - improved nav/feed row softness and spacing
- Added/updated tests:
  - `frontend/src/features/workspace/lib/feedIcons.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Workspace Nav IA + Readability Polish v3

- Navigation IA updates:
  - moved `Monitoring feeds` to a standalone section above `Folders`
  - kept stream routing semantics unchanged (`scope_type="stream"`)
  - added section-level monitoring collapse/expand toggle with persisted browser-local state
- Density and icon polish:
  - reduced feed icon scale (compact-first)
  - reduced nav row/action visual weight and tightened row spacing
  - kept favicon fallback behavior for feed icons
- Reader readability updates:
  - adopted paper-editorial default in light mode (warm paper background + dark neutral text)
  - switched frontend typography defaults to `IBM Plex Sans` (UI) and `Source Serif 4` (reader body)
  - tuned reader line length, line-height, and paragraph rhythm for long-form scanning
- Added/updated tests:
  - `frontend/src/entities/navigation/model.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Workspace UX Polish v4

- Added desktop pane resizing across both split boundaries:
  - navigation ↔ article list
  - article list ↔ reader
  - widths persisted in browser-local storage (`PANE_LAYOUT_KEY`)
- Added keyboard-accessible separators (`role="separator"`) with arrow/home/end controls.
- Updated monitoring header control from subtle icon-only toggle to visible labeled action (`Collapse` / `Expand`).
- Added slim workspace top bar with icon controls for:
  - dark/light mode toggle
  - settings navigation (`/account`)
- Removed density control from navigation/feed pane toolbar (to live on settings page later).
- Updated reader mark-read behavior:
  - when toggling unread -> read, selection now auto-advances to next article after mutation success
  - mark-unread does not auto-advance
- Stability improvement:
  - selected article id now falls back to first visible row when current id no longer exists in filtered results.
- Added/updated tests:
  - `frontend/src/features/workspace/lib/paneLayout.test.ts`
  - `frontend/src/features/workspace/hooks/usePaneResizing.test.tsx`
  - `frontend/src/features/workspace/lib/readActions.test.ts`
  - `frontend/src/entities/article/model.test.ts`
  - updated `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Frontend Planning Backlog (Paused)

- Session paused by user after theme/navigation polish on branch `feat/folder-nav-polish`.
- Resume plan for the next UI pass:
  1. Stabilize visual defaults:
     - keep `balanced` as default nav preset
     - keep `tight`/`airy` as optional variants, move the settings for this to a settings menu
  2. Folder panel final pass:
     - finalize row height, indent depth, and unread-count contrast values
     - verify truncation and menu discoverability at narrower widths
  3. Nav + list visual harmony:
     - align article list hover/selected/read states with softened pistachio light theme
     - keep reader pane styling unchanged
  4. Settings consolidation:
     - move display controls (nav preset/theme/density) into settings surface
     - keep quick theme toggle in top bar
  5. Wrap-up and merge readiness:
     - rerun `lint`, `typecheck`, `test`, `build`
     - open PR from `feat/folder-nav-polish` when approved

### UI Sprint: Settings Hub + Theme Presets (Completed Foundation Slice)

- Goal: complete a sleek, modern UI pass by centralizing preferences and shipping multiple prebuilt visual themes.
- Foundation slice outcome:
  1. Added multi-preset theme system with curated presets.
  2. Expanded `/account` into a settings hub for UI preferences.
  3. Removed duplicate workspace navigation display controls after settings migration.
  4. Added preset-aware theme tokens for coherent rail/nav/list/reader styling.

#### Delivered Vertical Slice

1. Theme model and persistence
   - Extended frontend UI state with `themePreset` and setter.
   - Added unified preference storage with backward-compatible legacy migration/synchronization.
   - Updated theme factory to accept both `themeMode` and `themePreset`.
2. Settings hub structure
   - Expand account/settings route into sectioned settings UI:
     - Appearance (theme mode + preset)
     - Reading/Layout (density and related display controls)
     - Account (existing identity summary)
3. Workspace cleanup
   - Kept topbar settings entry point and quick theme toggle.
   - Removed duplicated inline nav preset controls from workspace navigation.
4. Token-driven polish
   - Implemented semantic color/surface token contract for presets.
   - Updated shell surfaces to consume preset-aware tokens in light/dark.

#### Candidate Presets (Initial)

- Sift Classic (current green-forward baseline)
- Ocean Slate (cool blue/cyan accent)
- Graphite Violet (dark-forward premium)
- Warm Sand (light neutral with warm accent)

#### Verification (Completed)

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`

#### Next Priorities (UI Extensions, Completed 2026-02-16)

1. Perform deeper visual consistency pass across workspace panes per preset. (Completed)
2. Validate and tune contrast/interaction states for each preset in both theme modes. (Completed)
3. Expand settings UX with stronger accessibility affordances and responsive layout polish. (Completed)

### Backlog Reference

- Backlog source of truth is maintained in `docs/backlog.md`.
- This file remains the chronological session log only.
