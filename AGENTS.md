# Project Agent Notes

This file stores stable project context for future Codex sessions.

## Product Intent

- Build a self-hosted RSS/content aggregation portal.
- Prioritize backend quality and extension points.
- Build a modern, responsive frontend using React and MUI.

## Technical Direction (Stable)

- Python backend using FastAPI.
- Database-backed ingestion pipeline with SQLAlchemy.
- Plugin-ready core for enrichment/transformation/integration workflows.
- Backend is API-only under `/api/v1/*` (no server-rendered web routes).
- UI is a standalone React + MUI frontend in `frontend/` (Vite + TypeScript).
- Tooling standards: uv + Ruff + Pytest + Mypy.
- Ruff width: 120 chars.
- Alembic is the source of truth for schema changes.
- Preferred dev environment is the Dev Container full stack (`.devcontainer/`).

## Working Agreements

- Prefer modular monolith architecture for MVP.
- Avoid premature microservices; isolate via interfaces first.
- Branching workflow:
  - `main` is protected production.
  - `develop` is default integration branch.
  - create feature branches from `develop`, merge back to `develop`.
  - merge `develop` into `main` only when release-ready.
  - PRs into `main` must include exactly one release label: `release:major`, `release:minor`, or `release:patch`.
  - releases are automated from `main` merges with SemVer tags and GHCR image publish (`sift-backend`,
    `sift-frontend`).
- Prefer migration-first database evolution:
  - create migration,
  - apply migration,
  - keep `auto_create_tables` disabled outside local throwaway environments.
- Default development flow:
  - open in Dev Container (`.devcontainer/devcontainer.json`),
  - run stack via `.devcontainer/docker-compose.yml` (`app`, `frontend`, `worker`, `scheduler`, `db`, `redis`,
    `traefik`).
- Local IDE personalization:
  - keep personal VS Code config in `.vscode/extensions.local.json` and `.vscode/settings.local.json` (gitignored),
  - use `.vscode/*.example.json` as templates.

## Context Window Policy

- Keep `AGENTS.md` stable and concise; do not duplicate volatile backlog/history here.
- Active roadmap source of truth is `docs/backlog.md` only.
- Current implementation snapshot lives in `docs/current-state.md`.
- Session log is intentionally compact in `docs/session-notes.md` (rolling recent window).
- Older session history belongs in `docs/session-notes/archive/` (monthly archive files).

## Feature Direction Notes (Stable)

- Keyword streams should support many streams per user and evolve from deterministic rules to classifier-assisted
  matching.
- Classifier logic should remain plugin-driven with provider/model/version metadata and fault isolation.
- Search providers should be implemented via shared `search_provider` capability (`search_feeds(request)`), with
  ordered fallback and strict budgets/timeouts.
- Discover-feeds workflow should remain separate from provider adapter internals and consume shared provider
  infrastructure.
- LLM operations should use a shared plugin capability contract; on-demand summary is the first planned operation.
- Vector storage should stay plugin-boundary and optional (for example `pgvector`, Qdrant, Weaviate), not core-ingest
  mandatory.

## Planning Workflow For Future Sessions

1. Read `AGENTS.md`, `docs/current-state.md`, and `docs/backlog.md` first.
2. Read only the active spec(s) needed for the selected slice from `docs/specs/`.
3. Read `docs/session-notes.md` for recent context (latest 1-3 entries) only when needed.
4. Open `docs/session-notes/archive/*.md` only for deep historical investigation.
5. Implement one vertical slice fully (code + tests + docs updates).
6. End each session by updating:
   - `docs/session-notes.md` (rolling recent log + verification),
   - `docs/architecture.md` if architecture changed,
   - `docs/backlog.md` for active priority/deferred changes,
   - `docs/backlog-history.md` when completed items leave active backlog,
   - `docs/specs/` and `docs/specs/done/` when spec lifecycle changes.

## Backlog Governance

- Any long-horizon idea captured during sessions must be reviewed and added to `docs/backlog.md`.
- `docs/backlog.md` must contain only active remaining work (`Next`, `Deferred`).
- Completed or historical backlog entries must be moved to `docs/backlog-history.md`.
- `docs/specs/` must contain only active/planned specs.
- Completed feature specs must move to `docs/specs/done/` and linked references must be updated.
- Do not keep durable backlog items only in `docs/session-notes.md`; session notes are a rolling execution log.

## Where to Store Future Knowledge

- Stable project constraints/instructions: `AGENTS.md`.
- Architecture decisions and tradeoffs: `docs/architecture.md`.
- Current implementation snapshot and known constraints: `docs/current-state.md`.
- Rolling recent iteration log: `docs/session-notes.md`.
- Archived session history: `docs/session-notes/archive/`.
- Active backlog source of truth (`Next`, `Deferred`): `docs/backlog.md`.
- Backlog completion/history archive: `docs/backlog-history.md`.
- Active/planned feature specs: `docs/specs/`.
- Completed feature spec archive: `docs/specs/done/`.
