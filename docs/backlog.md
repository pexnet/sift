# Product Backlog

This is the source of truth for product backlog status and long-term roadmap items.

## Status Model

- `Done`: Implemented and verified in prior sessions.
- `Next`: Prioritized for upcoming implementation.
- `Deferred`: Captured for future delivery after current priorities.

## Next (Prioritized)

### Core Platform Priorities

1. Add stream-level ranking and prioritization controls.
2. Add classifier run persistence and model/version tracking.
3. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
4. Add scheduler and ingestion observability (metrics, latency, failures).

### Next UI Slice

1. Monitoring feed management v1 completed on 2026-02-16.
2. Monitoring search language v1 completed on 2026-02-16.
3. Monitoring feed management v2 is now in progress:
   - completed on 2026-02-16: historical backfill execution endpoint and UI success feedback
   - completed on 2026-02-16: regex matcher rules in monitoring definition management
   - completed on 2026-02-16: richer explainability baseline (captured match reasons surfaced in list/reader)
   - completed on 2026-02-16: plugin matcher config baseline (stream-level classifier config JSON)
   - completed on 2026-02-16: structured match evidence payloads (keyword/regex snippets + classifier evidence) surfaced in reader metadata
   - completed on 2026-02-16: inline reader highlighting toggle using structured evidence values
   - completed on 2026-02-16: offset-aware reader highlighting with jump-to-highlight evidence panel
   - next: extend plugin contracts to emit richer multi-finding evidence blocks (provider-native snippets/scores)

## Done (History)

### Core and Platform Foundations

1. API-only FastAPI backend surface under `/api/v1/*`.
2. Auth foundation:
   - local auth identity provider
   - Argon2 password hashing
   - cookie sessions via `user_sessions`
3. Feed/article authenticated ownership model (`feeds.owner_id`).
4. Feed ingestion pipeline:
   - RSS/Atom fetch + parse
   - raw payload storage
   - normalized article creation
   - plugin ingest hook dispatch
5. Dedupe foundations:
   - feed+source-id dedupe
   - cross-feed canonical dedupe with normalized URL/content fingerprint + duplicate linking/confidence
6. Persisted rule engine and ingestion enforcement.
7. Keyword streams:
   - persisted definitions
   - stream membership matching
   - stream article views
8. Stream classifier foundation:
   - `rules_only`, `classifier_only`, `hybrid`
   - plugin name + confidence threshold controls
9. Redis/RQ scheduler-worker orchestration:
   - queue wiring
   - worker process
   - scheduler loop with due-feed enqueueing
   - stable dedupe job IDs (`ingest-<feed_id>`) with legacy lookup compatibility
10. Feed folders:
   - per-user folder model
   - folder CRUD
   - feed-to-folder assignment
11. OPML import and development seed bootstrap:
   - per-user OPML dedupe/import reporting
   - seed creates default local user
   - seed imports folders/feeds
   - Inoreader monitoring feeds mapped to keyword streams
12. Monitoring search language v1:
   - parser + evaluator for `AND`, `OR`, `NOT`, parentheses, and quoted phrases
   - suffix wildcard support (`term*`) and fuzzy token support (`term~1`, `term~2`)
   - persisted stream expression field (`keyword_streams.match_query`) with create/update validation
   - stream matching now evaluates saved query expressions
   - article search now supports advanced query syntax with clear syntax errors

### Frontend Workspace and UX History

1. Reader-first workspace delivered:
   - `/app` 3-pane shell (navigation/list/reader)
   - responsive behavior for desktop/tablet/mobile
   - core keyboard shortcuts (`j/k`, `o`, `m`, `s`, `/`)
2. Workspace data/navigation foundations:
   - unified hierarchy mapping for system/folder/feed/stream scopes
   - monitoring feeds section in navigation
3. Folder/feed management flows integrated in SPA.
4. Reader improvements:
   - sanitized rich content rendering
   - reader action wiring (`read`, `save`, `open original`, `prev`, `next`)
5. Multiple workspace polish iterations:
   - navigation IA and readability tuning
   - section collapse/expand persistence
   - pane resizing with persistence and keyboard-accessible separators
   - compact visual/interaction refinements
6. Settings hub and theme system:
   - `/account` as centralized settings
   - unified UI preferences model (`themeMode`, `themePreset`, `density`, `navPreset`)
   - multiple curated theme presets
   - preset-aware tokens and MUI palette alignment
   - reset-to-defaults action
   - accessibility and keyboard interaction hardening
7. Monitoring feed management v1:
   - `/account/monitoring` stream-backed monitoring definition CRUD
   - optional backfill action entry point with explicit unavailable-state feedback
   - matched monitoring stream explainability labels in article list and reader
8. Frontend quality gates repeatedly verified on delivered slices (`lint`, `typecheck`, `test`, `build`).
9. Monitoring feed management v2 (backfill execution baseline):
   - backend endpoint implemented: `POST /api/v1/streams/{stream_id}/backfill`
   - endpoint recalculates stream matches across existing user articles
   - stale stream-match rows are replaced with recomputed results
   - monitoring UI now reports concrete backfill completion counts
10. Monitoring feed management v2 (regex matcher expansion baseline):
   - stream definitions now support include/exclude regex pattern lists
   - backend validates regex patterns on stream create/update and returns clear validation errors
   - ingest matching and backfill matching now enforce regex include/exclude rules
   - monitoring UI supports editing regex rules with persistence through stream CRUD APIs
11. Monitoring feed explainability baseline:
   - match reason is persisted per stream/article match (`keyword_stream_matches.match_reason`)
   - reasons are generated from query/keyword/regex/source/language/classifier match decisions
   - article list/detail APIs now expose per-stream match reasons
   - workspace list/reader now render `Why matched` summaries for monitoring stream matches
12. Monitoring plugin matcher config baseline:
   - stream definitions now support persisted classifier config JSON payloads (`classifier_config`)
   - backend validates classifier config payload shape/size/JSON-serializability
   - classifier plugins receive per-stream config in classifier execution context
   - monitoring UI supports editing classifier config JSON and validates JSON format before submit
13. Help documentation surface:
   - authenticated `/help` route implemented
   - focused help content added for monitoring feed configuration and search syntax reference
   - settings and monitoring pages now include help entry links
14. Workspace UX follow-up:
   - left rail now includes a direct Help action (`/help`)
   - article list action now supports scope-aware mark-read execution with confirmation
   - action copy clarified to `Mark all in scope as read`

### Completed Session Index (Chronological)

1. 2026-02-15:
   - API-only architecture baseline finalized.
   - Workspace UI slices delivered (`Folder + Reader v1`, modernization, nav/readability polish, UX polish v4).
2. 2026-02-16:
   - Planning alignment and reprioritization updates completed.
   - Settings hub foundation delivered.
   - Settings accessibility + route tests delivered.
   - Preset consistency/contrast/settings UX extension pass completed.
   - Theme consistency follow-up and doc alignment completed.
3. 2026-02-16:
   - Monitoring feed management v1 delivered (route + CRUD + explainability + backfill entry point).
4. 2026-02-16:
   - Monitoring search language v1 delivered (parser + stream persistence + matching + monitoring UI field + tests).
5. 2026-02-16:
   - Monitoring feed management v2 baseline delivered (historical backfill execution path).
6. 2026-02-16:
   - Monitoring feed management v2 regex baseline delivered (include/exclude regex matching rules).
7. 2026-02-16:
   - Monitoring explainability baseline delivered (persisted match reasons + workspace rendering).
8. 2026-02-16:
   - Monitoring plugin matcher config baseline delivered (classifier config persistence + UI + plugin context wiring).

Reference for detailed per-session implementation and verification logs: `docs/session-notes.md`.

## Deferred (Not Prioritized Yet)

### 1) Feed Health + Edit Surface

- Add a dedicated feed status/edit page showing per-feed health and operational metadata.
- Include feed freshness and cadence metrics:
  - last successful ingest time
  - recent ingest failures and error reason
  - estimated article frequency (for example: articles/day and 7-day rolling cadence)
- Add feed lifecycle actions:
  - pause/resume scheduled ingestion
  - archive/unarchive feed

### 2) Monitoring Feed Search Management v2

- Add expanded management capabilities for monitoring feed definitions.
- Support multiple matcher types:
  - query language composition beyond v1 boolean/phrase/wildcard/fuzzy operators
  - regex rules (baseline include/exclude regex support is implemented)
  - plugin-provided matchers for advanced semantic/domain-specific discovery (config baseline is implemented)
- Baseline manual backfill execution is implemented; optional create/update-triggered historical pass remains deferred.
- Add article-view explainability:
  - highlight matched keyword/regex spans
  - render plugin finding snippets/reasons (baseline textual reason summaries are implemented)

### 3) Dashboard as Daily Command Center

- Introduce a dashboard route focused on first-read triage and daily priorities.
- Add prioritization controls to weight content sources (regular feeds vs monitoring feeds vs other scopes).
- Candidate dashboard widgets:
  - latest unread by priority
  - high-signal monitoring matches
  - feed health summary (errors/stale feeds)
  - saved/flagged follow-up queue

### 4) Duplicate Detection Visibility (Iteration 1)

- Provide an initial duplicate-candidate screen accessible from Settings.
- Keep first iteration read-focused:
  - list suspected duplicate groups
  - show confidence/source metadata
  - link out to canonical article + variants

### 5) Plugin Backlog Ideas

- LLM summarization plugin:
  - generate concise article summaries
  - first provider target: Ollama Cloud
- Vector-similarity plugin:
  - embeddings-backed article/topic similarity
  - supports related-content surfacing and future semantic monitoring workflows

### 6) Trends Detection for Selected Feed Folders

- Add a deferred trends feature that detects emerging topics across selected feed folders.
- Intended use cases:
  - dashboard briefing cards ("what is trending today")
  - editor/research triage for fast signal detection
- Candidate approach:
  - rolling-window term/keyphrase extraction and scoring
  - compare short-term lift vs longer baseline to estimate trend momentum
  - allow user-selected folder scope as trend input
- Output explainability:
  - representative keywords/keyphrases
  - supporting article count and source spread
  - links into matching article lists for drill-down

### 7) Advanced Search Query Acceleration

- Keep v1 search semantics stable, but defer DB-side acceleration work.
- Candidate acceleration paths:
  - PostgreSQL `tsvector`/`tsquery` indexing for boolean/phrase-oriented filtering
  - `pg_trgm` indexes for wildcard/fuzzy support where needed
  - hybrid strategy (DB pre-filter + app-layer exact evaluator) for semantic parity
- Goal:
  - avoid full in-memory scan for advanced expressions on large article sets
  - preserve current query-language behavior and error model

### Suggested Deferred Delivery Sequence

1. Feed health/edit page (operability baseline).
2. Monitoring feed management v2 (keyword/regex + historical backfill + match highlighting).
3. Dashboard v1 (priority inbox and command-center widgets).
4. Duplicate-candidate settings view.
5. Trends detection for selected feed folders (dashboard-oriented).
6. Advanced search query acceleration (PostgreSQL-oriented).
7. Plugin implementations (LLM summary, vector similarity) behind existing plugin contracts.
