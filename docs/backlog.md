# Product Backlog

This is the source of truth for active product backlog status and remaining roadmap items.

Historical/completed backlog items are archived in [docs/backlog-history.md](backlog-history.md).

## Status Model

- `Next`: Prioritized for upcoming implementation.
- `Deferred`: Captured for future delivery after current priorities.

## Next (Prioritized)

### Core Platform Priorities

1. Add stream-level ranking and prioritization controls.
2. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
3. Add scheduler and ingestion observability (metrics, latency, failures).

### Next UI Slice

- No active prioritized UI slice is currently queued.
- Most recently completed: workspace action iconification v1 (completed on 2026-02-18; archived in
  `docs/backlog-history.md`).

### Linked Specifications

- Discover feeds v1: [docs/specs/feed-recommendations-v1.md](specs/feed-recommendations-v1.md)
- Plugin UI organization v1: [docs/specs/plugin-ui-organization-v1.md](specs/plugin-ui-organization-v1.md)
- Plugin configuration registry v1: [docs/specs/plugin-configuration-registry-v1.md](specs/plugin-configuration-registry-v1.md)
- Silent feeds v1: [docs/specs/silent-feeds-v1.md](specs/silent-feeds-v1.md)
- Full article fetch on-demand v1: [docs/specs/full-article-fetch-on-demand-v1.md](specs/full-article-fetch-on-demand-v1.md)
- Workspace action iconification v1:
  [docs/specs/workspace-action-iconification-v1.md](specs/workspace-action-iconification-v1.md)
- Planning decision (2026-02-17): Discover feeds v1 is stream-driven via separate `discovery_streams` and does not
  use saved/starred article seeds in v1.
- Planning decision (2026-02-17): Discover feeds provider strategy should start with an ordered provider chain and
  enforce free-tier-safe per-provider request budgets/rate limits by default.

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

### 2) Monitoring Feed Search Management v2 Follow-Ups

- Add expanded management capabilities for monitoring feed definitions.
- Support additional matcher composition capabilities beyond current baseline semantics.
- Add optional create/update-triggered historical matching pass.
- Continue article-view explainability refinements for plugin findings and richer query evidence rendering.

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
- Spec reference: [docs/specs/article-llm-summary-on-demand-v1.md](specs/article-llm-summary-on-demand-v1.md)

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

### 8) Plugin UI Areas + Centralized Plugin Configuration

- Add a dedicated plugin section in workspace navigation where each enabled plugin owns its own folder/area.
- Initial target examples:
  - `Discover feeds` plugin area
  - `Bluesky` plugin area (when plugin is implemented)
- Introduce centralized plugin registry configuration (single file) for:
  - plugin metadata and route/UI area configuration
  - enable/disable toggles per plugin
  - plugin-specific settings payloads
- Keep secrets in environment variables and reference them from config.
- Plan compatibility mode to migrate from legacy `plugin_paths` to registry-based plugin activation.

### 9) Silent Feeds for Monitoring-Only Population

- Add feed-level `silent` mode for high-noise feeds that should populate monitoring streams without creating unread
  backlog.
- Silent feeds should:
  - ingest and match monitoring rules exactly like normal feeds
  - auto-mark ingested articles as read
  - keep unread counts at zero after ingest/toggle processing
- When a feed is switched to silent, existing unread for that feed should be bulk-marked read.
- Spec reference: [docs/specs/silent-feeds-v1.md](specs/silent-feeds-v1.md)

### 10) Discover Feeds (Discovery Streams)

- Add the `Discover feeds` vertical slice using separate `discovery_streams` (not monitoring stream reuse).
- Implement discovery-stream generation and recommendation decision flow:
  - discovery stream CRUD
  - manual generation trigger
  - recommendation accept/deny/reset workflow
- Keep provider execution behind ordered adapters with free-tier-safe budgets/rate limits.
- Spec reference: [docs/specs/feed-recommendations-v1.md](specs/feed-recommendations-v1.md)

### 11) OIDC Provider Integration

- Add external identity provider support on top of existing `auth_identities` foundation.
- Delivery order:
  - Google first
  - then Azure/Apple
- Keep current local auth provider behavior unchanged as fallback.

### 12) Full Article Fetch On-Demand

- Add user-triggered `Fetch full article` action in reader to retrieve the full source-page content on demand.
- Persist extracted fulltext separately from feed excerpt content and show source state in reader.
- Keep initial version manual/on-demand only (no global auto-fetch).
- Spec reference: [docs/specs/full-article-fetch-on-demand-v1.md](specs/full-article-fetch-on-demand-v1.md)

### Suggested Deferred Delivery Sequence

1. Feed health/edit page (operability baseline).
2. Monitoring feed management v2 follow-ups.
3. Dashboard v1 (priority inbox and command-center widgets).
4. Discover feeds v1 (discovery streams + recommendation decisions).
5. Duplicate-candidate settings view.
6. Trends detection for selected feed folders (dashboard-oriented).
7. Advanced search query acceleration (PostgreSQL-oriented).
8. Plugin UI areas + centralized plugin configuration.
9. Plugin implementations (LLM summary, vector similarity) behind existing plugin contracts.
10. Silent feeds for monitoring-only population.
11. OIDC provider integration (Google, then Azure/Apple).
12. Full article fetch on-demand (reader-triggered).
