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

## Active Priorities

1. Search provider plugin platform v1 (ordered provider fallback + strict budgets/timeouts).

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
