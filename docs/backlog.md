# Product Backlog

This is the source of truth for active product backlog status and remaining roadmap items.

Historical/completed backlog items are archived in [docs/backlog-history.md](backlog-history.md).

## Status Model

- `Next`: Prioritized for upcoming implementation.
- `Deferred`: Captured for future delivery after current priorities.

## Next (Prioritized)

### Core Platform Priorities

1. Plugin configuration registry v1 follow-ups:
  - add config security enforcement/tests for env-ref secret handling
  - add provider budget/rate-limit contract tests for discovery-oriented plugin settings
  - spec: [docs/specs/plugin-configuration-registry-v1.md](specs/plugin-configuration-registry-v1.md)
2. Resume dependency feature slices after plugin closure:
  - stream-level ranking/prioritization controls
  - scheduler and ingestion observability (metrics, latency, failures; spec:
    [docs/specs/scheduler-ingestion-observability-v1.md](specs/scheduler-ingestion-observability-v1.md))

### Next UI Slice

1. No additional UI-only polish slice is active; core platform priorities are now primary.
2. Most recently completed:
  - desktop reader/workspace polish v2 (closed on 2026-02-22):
    - desktop screenshot QA evidence: `artifacts/desktop-review-2026-02-21T23-27-06-123Z`
    - captured at `1920x1080` and `1366x768` across `/app`, `/account`, `/account/feed-health`,
      `/account/monitoring`, and `/help`
    - close verification rerun: `npm --prefix frontend run lint`, `npm --prefix frontend run typecheck`,
      `npm --prefix frontend run test`, `npm --prefix frontend run build`
  - workspace + settings management UI touchups v1 (completed on 2026-02-21; spec archived in
    `docs/specs/done/workspace-settings-management-ui-touchups-v1.md`)
  - feed health + edit surface v1 (completed on 2026-02-19; archived in `docs/backlog-history.md`; spec archived in
    `docs/specs/done/feed-health-edit-surface-v1.md`).

### Linked Specifications

- Discover feeds v1: [docs/specs/feed-recommendations-v1.md](specs/feed-recommendations-v1.md)
- Plugin UI organization v1: [docs/specs/plugin-ui-organization-v1.md](specs/plugin-ui-organization-v1.md)
- Plugin configuration registry v1: [docs/specs/plugin-configuration-registry-v1.md](specs/plugin-configuration-registry-v1.md)
- Silent feeds v1: [docs/specs/silent-feeds-v1.md](specs/silent-feeds-v1.md)
- Full article fetch on-demand v1: [docs/specs/full-article-fetch-on-demand-v1.md](specs/full-article-fetch-on-demand-v1.md)
- Dashboard command center v1: [docs/specs/dashboard-command-center-v1.md](specs/dashboard-command-center-v1.md)
- Stream ranking/prioritization controls v1:
  [docs/specs/stream-ranking-prioritization-controls-v1.md](specs/stream-ranking-prioritization-controls-v1.md)
- Feed health ops panel v1: [docs/specs/feed-health-ops-panel-v1.md](specs/feed-health-ops-panel-v1.md)
- Scheduler/ingestion observability v1:
  [docs/specs/scheduler-ingestion-observability-v1.md](specs/scheduler-ingestion-observability-v1.md)
- Monitoring signal scoring v1: [docs/specs/monitoring-signal-scoring-v1.md](specs/monitoring-signal-scoring-v1.md)
- Trends detection dashboard v1: [docs/specs/trends-detection-dashboard-v1.md](specs/trends-detection-dashboard-v1.md)
- Planning decision (2026-02-17): Discover feeds v1 is stream-driven via separate `discovery_streams` and does not
  use saved/starred article seeds in v1.
- Planning decision (2026-02-17): Discover feeds provider strategy should start with an ordered provider chain and
  enforce free-tier-safe per-provider request budgets/rate limits by default.

## Deferred (Not Prioritized Yet)

### 1) Monitoring Feed Search Management v2 Follow-Ups

- Add expanded management capabilities for monitoring feed definitions.
- Support additional matcher composition capabilities beyond current baseline semantics.
- Add optional create/update-triggered historical matching pass.
- Continue article-view explainability refinements for plugin findings and richer query evidence rendering.

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
  - [docs/specs/feed-recommendations-v1.md](specs/feed-recommendations-v1.md)
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

### 8) Discover Feeds (Discovery Streams)

- Add the `Discover feeds` vertical slice using separate `discovery_streams` (not monitoring stream reuse).
- Implement discovery-stream generation and recommendation decision flow:
  - discovery stream CRUD
  - manual generation trigger
  - recommendation accept/deny/reset workflow
- Keep provider execution behind ordered adapters with free-tier-safe budgets/rate limits.
- Spec reference: [docs/specs/feed-recommendations-v1.md](specs/feed-recommendations-v1.md)

### 9) OIDC Provider Integration

- Add external identity provider support on top of existing `auth_identities` foundation.
- Delivery order:
  - Google first
  - then Azure/Apple
- Keep current local auth provider behavior unchanged as fallback.

### 10) Full Article Fetch On-Demand

- Add user-triggered `Fetch full article` action in reader to retrieve the full source-page content on demand.
- Persist extracted fulltext separately from feed excerpt content and show source state in reader.
- Keep initial version manual/on-demand only (no global auto-fetch).
- Spec reference: [docs/specs/full-article-fetch-on-demand-v1.md](specs/full-article-fetch-on-demand-v1.md)

### 11) Vector Database Integration Infrastructure

- Move vector-database integration out of immediate `Next` and keep it as a later deferred capability.
- Add plugin-boundary vector infrastructure for embeddings and semantic matching workflows.
- Keep vector storage optional and provider-pluggable (for example `pgvector`, Qdrant, Weaviate).
- Preserve core-ingestion independence so vector infrastructure remains non-blocking for baseline feeds/streams.

### 12) Mobile UX Planning (Dedicated Session)

- Keep current mobile runtime in read-focused mode.
- Run a separate mobile planning/design session later to define:
  - mobile-specific navigation and reading ergonomics
  - deferred settings/admin re-entry strategy (if any)
  - final mobile density/accessibility targets and test matrix
- Do not block current desktop polish and core platform priorities on this planning slice.

### Suggested Deferred Delivery Sequence

1. Monitoring feed management v2 follow-ups.
2. Dashboard v1 (priority inbox and command-center widgets; start only after dashboard spec-gate checklist is complete).
3. Discover feeds v1 (discovery streams + recommendation decisions).
4. Duplicate-candidate settings view.
5. Trends detection for selected feed folders (dashboard-oriented).
6. Advanced search query acceleration (PostgreSQL-oriented).
7. Vector-database integration infrastructure (plugin-boundary embeddings support).
8. Plugin implementations (LLM summary, vector similarity) behind existing plugin contracts.
9. Silent feeds for monitoring-only population.
10. OIDC provider integration (Google, then Azure/Apple).
11. Full article fetch on-demand (reader-triggered).
