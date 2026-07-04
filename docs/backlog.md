# Product Backlog

This is the source of truth for active product backlog status and remaining roadmap items.

Historical/completed backlog items are archived in [docs/backlog-history.md](backlog-history.md).
Current implementation snapshot is maintained in [docs/current-state.md](current-state.md).

## Status Model

- `Next`: Prioritized for upcoming implementation.
- `Deferred`: Captured for future delivery after current priorities.

## Next (Prioritized)

### Core Platform Priorities

1. Monitoring feed search management v2 continued:
   - continue explainability refinements for plugin/query evidence surfaces.

### Next UI Slice

1. No additional UI-only polish slice is active; core platform priorities are now primary.
2. Completed UI milestones are tracked in `docs/backlog-history.md` and `docs/specs/done/`.

### Active Linked Specifications

- Silent feeds v1: [docs/specs/silent-feeds-v1.md](specs/silent-feeds-v1.md)
- Dashboard command center v1: [docs/specs/dashboard-command-center-v1.md](specs/dashboard-command-center-v1.md)
- Stream ranking/prioritization controls v1:
  [docs/specs/stream-ranking-prioritization-controls-v1.md](specs/stream-ranking-prioritization-controls-v1.md)
- Feed health ops panel v1: [docs/specs/feed-health-ops-panel-v1.md](specs/feed-health-ops-panel-v1.md)
- Monitoring signal scoring v1: [docs/specs/monitoring-signal-scoring-v1.md](specs/monitoring-signal-scoring-v1.md)
- Trends detection dashboard v1: [docs/specs/trends-detection-dashboard-v1.md](specs/trends-detection-dashboard-v1.md)

## Deferred (Not Prioritized Yet)

### 1) Stream-Level Ranking/Prioritization Controls

- Defer stream-ranking implementation while monitoring and dashboard dependency slices are prioritized.
- Spec reference:
  - [docs/specs/stream-ranking-prioritization-controls-v1.md](specs/stream-ranking-prioritization-controls-v1.md)

### 2) Dashboard as Daily Command Center (Full Card/Data Rollout)

- Complete the command-center experience at `/app/dashboard` while keeping existing left workspace chrome:
  - rail + navigation tree remain visible
  - dashboard fills the remaining workspace content area
- Add prioritization controls to weight content sources (regular feeds vs monitoring feeds vs other scopes).
- Candidate dashboard cards:
  - prioritized unread queue
  - high-value monitoring feed signals
  - feed health ops summary (errors/stale/freshness/queue lag)
  - saved follow-up queue
  - trends card (explicit unavailable state until trend dependency is implemented)
  - discovery candidates (feed recommendations + monitoring-first candidate articles)
- Optional future cards:
  - alerts
  - follow-up detail tab
- Dashboard spec gate checklist (required before implementation starts):
  - [docs/specs/done/dashboard-shell-plugin-host-v1.md](specs/done/dashboard-shell-plugin-host-v1.md)
  - [docs/specs/dashboard-command-center-v1.md](specs/dashboard-command-center-v1.md)
  - [docs/specs/stream-ranking-prioritization-controls-v1.md](specs/stream-ranking-prioritization-controls-v1.md)
  - [docs/specs/feed-health-ops-panel-v1.md](specs/feed-health-ops-panel-v1.md)
  - [docs/specs/monitoring-signal-scoring-v1.md](specs/monitoring-signal-scoring-v1.md)
  - [docs/specs/trends-detection-dashboard-v1.md](specs/trends-detection-dashboard-v1.md)
  - [docs/specs/done/search-provider-plugin-v1.md](specs/done/search-provider-plugin-v1.md)
  - [docs/specs/done/feed-recommendations-v1.md](specs/done/feed-recommendations-v1.md)
- Rule:
  - dashboard implementation starts only after all checklist dependency specs are drafted and linked.

### 3) Duplicate Detection Visibility (Iteration 1)

- Provide an initial duplicate-candidate screen accessible from Settings.
- Keep first iteration read-focused:
  - list suspected duplicate groups
  - show confidence/source metadata
  - link out to canonical article + variants

### 4) Plugin Backlog Ideas

- LLM summarization plugin:
  - generate concise article summaries
  - first provider target: Ollama Cloud
- Vector-similarity plugin:
  - embeddings-backed article/topic similarity
  - supports related-content surfacing and future semantic monitoring workflows
- Spec reference: [docs/specs/article-llm-summary-on-demand-v1.md](specs/article-llm-summary-on-demand-v1.md)

### 5) Trends Detection for Selected Feed Folders

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

### 6) Advanced Search Query Acceleration

- Keep v1 search semantics stable, but defer DB-side acceleration work.
- Candidate acceleration paths:
  - PostgreSQL `tsvector`/`tsquery` indexing for boolean/phrase-oriented filtering
  - `pg_trgm` indexes for wildcard/fuzzy support where needed
  - hybrid strategy (DB pre-filter + app-layer exact evaluator) for semantic parity
- Goal:
  - avoid full in-memory scan for advanced expressions on large article sets
  - preserve current query-language behavior and error model

### 7) Silent Feeds for Monitoring-Only Population

- Add feed-level `silent` mode for high-noise feeds that should populate monitoring streams without creating unread
  backlog.
- Silent feeds should:
  - ingest and match monitoring rules exactly like normal feeds
  - auto-mark ingested articles as read
  - keep unread counts at zero after ingest/toggle processing
- When a feed is switched to silent, existing unread for that feed should be bulk-marked read.
- Spec reference: [docs/specs/silent-feeds-v1.md](specs/silent-feeds-v1.md)

### 8) OIDC Provider Integration

- Add external identity provider support on top of existing `auth_identities` foundation.
- Delivery order:
  - Google first
  - then Azure/Apple
- Keep current local auth provider behavior unchanged as fallback.

### 9) Vector Database Integration Infrastructure

- Move vector-database integration out of immediate `Next` and keep it as a later deferred capability.
- Add plugin-boundary vector infrastructure for embeddings and semantic matching workflows.
- Keep vector storage optional and provider-pluggable (for example `pgvector`, Qdrant, Weaviate).
- Preserve core-ingestion independence so vector infrastructure remains non-blocking for baseline feeds/streams.

### 10) Mobile UX Planning (Dedicated Session)

- Keep current mobile runtime in read-focused mode.
- Run a separate mobile planning/design session later to define:
  - mobile-specific navigation and reading ergonomics
  - deferred settings/admin re-entry strategy (if any)
  - final mobile density/accessibility targets and test matrix
- Do not block current desktop polish and core platform priorities on this planning slice.

### Suggested Deferred Delivery Sequence

1. Dashboard v1 (priority inbox and command-center widgets; start only after dashboard spec-gate checklist is complete).
2. Stream-level ranking/prioritization controls.
3. Duplicate-candidate settings view.
4. Trends detection for selected feed folders (dashboard-oriented).
5. Advanced search query acceleration (PostgreSQL-oriented).
6. Vector-database integration infrastructure (plugin-boundary embeddings support).
7. Plugin implementations (LLM summary, vector similarity) behind existing plugin contracts.
8. Silent feeds for monitoring-only population.
9. OIDC provider integration (Google, then Azure/Apple).
