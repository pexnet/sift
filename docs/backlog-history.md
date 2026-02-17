# Backlog History

This file archives completed and historical backlog items that were removed from the active backlog.

Active backlog source of truth: [docs/backlog.md](backlog.md)

## Archived Backlog History (Moved on 2026-02-17)

### Monitoring UI Milestones (Previously in Active Next UI Slice)

1. Monitoring feed management v1 completed on 2026-02-16.
2. Monitoring search language v1 completed on 2026-02-16.
3. Monitoring feed management v2 completed milestones:
   - completed on 2026-02-16: historical backfill execution endpoint and UI success feedback
   - completed on 2026-02-16: regex matcher rules in monitoring definition management
   - completed on 2026-02-16: richer explainability baseline (captured match reasons surfaced in list/reader)
   - completed on 2026-02-16: plugin matcher config baseline (stream-level classifier config JSON)
   - completed on 2026-02-16: structured match evidence payloads (keyword/regex snippets + classifier evidence) surfaced in reader metadata
   - completed on 2026-02-16: inline reader highlighting toggle using structured evidence values
   - completed on 2026-02-16: offset-aware reader highlighting with jump-to-highlight evidence panel
   - completed on 2026-02-17: plugin contracts now emit richer multi-finding classifier evidence blocks
     (provider-native snippets/scores, optional offsets)

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
13. Classifier run persistence and model/version tracking:
   - persisted `stream_classifier_runs` records for classifier executions during ingest/backfill
   - captured plugin/provider/model/version metadata, confidence/threshold, and run status
   - added diagnostics API endpoint: `GET /api/v1/streams/{stream_id}/classifier-runs`

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
