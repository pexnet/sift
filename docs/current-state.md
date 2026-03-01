# Current State Snapshot

Last updated: 2026-03-01

This file is a compact, high-signal snapshot for session startup.
For active priorities, use [docs/backlog.md](backlog.md).
For architecture details, use [docs/architecture.md](architecture.md).

## Runtime and Platform Status

- Backend: FastAPI API-only service under `/api/v1/*`.
- Frontend: standalone React + MUI SPA (`frontend/`) using Vite + TypeScript.
- Background processing: Redis + RQ with scheduler/worker ingestion orchestration.
- Plugin runtime: centralized registry (`config/plugins.yaml`) with capability-gated dispatch.

## Implemented Milestones (Recent)

- Scheduler/ingestion observability v1 completed:
  - request correlation,
  - structured API/scheduler/worker events,
  - Prometheus-compatible metrics,
  - dedicated scheduler and worker scrape endpoints,
  - local observability bootstrap in `ops/observability/`.
- Full article fetch on-demand v1 completed:
  - `POST /api/v1/articles/{article_id}/fulltext/fetch`,
  - persisted fulltext and reader integration.
- Plugin platform baseline completed:
  - registry/runtime cutover,
  - timeout/fault isolation,
  - diagnostics endpoint,
  - workspace plugin-area host,
  - dashboard shell host baseline.
- Search provider platform v1 slice 1 implemented:
  - plugin capability contract (`search_provider` / `search_feeds`) wired in runtime manager,
  - registry validation for `settings.search_provider` provider chain/budgets and allowlisted providers,
  - authenticated baseline APIs:
    - `GET /api/v1/search/providers`
    - `POST /api/v1/search/feeds`
- Search provider platform v1 slice 2 implemented:
  - ordered provider fallback orchestration (`searxng` -> `brave_search` by config),
  - strict in-process budget/rate enforcement (`max_requests_per_run`, `max_requests_per_day`, `min_interval_ms`),
  - runtime provider adapters baseline:
    - `searxng`
    - `brave_search`
- Search provider platform v1 slice 3 implemented:
  - persistent daily provider budget ledger (`search_provider_budget_daily`),
  - DB-backed hard enforcement for `max_requests_per_day` and `min_interval_ms` across restarts/processes,
  - explicit warning metadata in search responses (`warning_details` with stable warning codes).
- Search provider platform v1 completed and archived:
  - provider adapter hardening with warning-coded timeout/network/http/json/payload handling,
  - runtime candidate URL normalization and de-duplication,
  - archived spec: `docs/specs/done/search-provider-plugin-v1.md`.
- Plugin architecture hardening implemented:
  - shared plugin capability metadata contract (`src/sift/plugins/capabilities.py`),
  - runtime-loaded plugin registry snapshot exposed by plugin manager,
  - search/plugin API surfaces now resolve plugin config from runtime snapshot (not per-request file reload).

## Active Priorities

1. Discover feeds v1 (discovery streams + recommendation decisions) on top of completed search-provider infrastructure.

Deferred for now:

- Stream-level ranking/prioritization controls.

## Known Product Constraints

- Feed URL uniqueness is currently global (shared-feed/subscription redesign deferred).
- OIDC providers are intentionally deferred (local auth remains primary).
- Dashboard full command-center card/data rollout is deferred behind spec-gate dependencies.

## Quick Links

- Backlog (active plan): [docs/backlog.md](backlog.md)
- Backlog history (completed): [docs/backlog-history.md](backlog-history.md)
- Active specs: `docs/specs/`
- Completed specs: `docs/specs/done/`
- Recent session log: [docs/session-notes.md](session-notes.md)
- Session archives: `docs/session-notes/archive/`
