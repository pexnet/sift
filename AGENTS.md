# Project Agent Notes

This file stores persistent project context for future Codex sessions.

## Product Intent

- Build a self-hosted RSS/content aggregation portal.
- Prioritize backend quality and extension points.
- Build a modern, responsive, sleek frontend using React and MUI (Material UI).

## Technical Direction (Current)

- Python backend using FastAPI.
- Database-backed ingestion pipeline with SQLAlchemy.
- Plugin-ready core for enrichment/transformation/integration use cases.
- Backend is API-only FastAPI service (`/api/v1/*`), with no server-rendered web routes.
- UI is a standalone React + MUI frontend in `frontend/` (Vite + TypeScript).
- Tooling standards: uv + Ruff + Pytest + Mypy.
- Ruff width: 120 chars.
- Alembic is the source of truth for schema changes.
- Preferred dev environment is Dev Container-based full stack (`.devcontainer/`).

## Working Agreements

- Prefer modular monolith architecture for MVP.
- Avoid premature microservices; isolate via interfaces first.
- Prefer migration-first database evolution:
  - Create migration.
  - Apply migration.
  - Keep `auto_create_tables` disabled outside local throwaway environments.
- All major changes should update:
  - `docs/architecture.md` for architecture-impacting decisions.
  - `docs/session-notes.md` for decision log + next steps.
- Default development flow:
  - Open in Dev Container (`.devcontainer/devcontainer.json`).
  - Use `.devcontainer/docker-compose.yml` stack for `app`, `frontend`, `worker`, `scheduler`, `db`, `redis`, and `traefik`.
- Local IDE personalization:
  - Keep personal VS Code config in `.vscode/extensions.local.json` and `.vscode/settings.local.json` (gitignored).
  - Use `.vscode/*.example.json` as templates.

## Current API Surface (MVP Core)

- `GET /api/v1/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/rules`
- `POST /api/v1/rules`
- `PATCH /api/v1/rules/{rule_id}`
- `DELETE /api/v1/rules/{rule_id}`
- `GET /api/v1/streams`
- `POST /api/v1/streams`
- `PATCH /api/v1/streams/{stream_id}`
- `DELETE /api/v1/streams/{stream_id}`
- `GET /api/v1/streams/{stream_id}/articles`
- `GET /api/v1/feeds`
- `POST /api/v1/feeds`
- `POST /api/v1/feeds/{feed_id}/ingest`
- `PATCH /api/v1/feeds/{feed_id}/folder`
- `GET /api/v1/folders`
- `POST /api/v1/folders`
- `PATCH /api/v1/folders/{folder_id}`
- `DELETE /api/v1/folders/{folder_id}`
- `POST /api/v1/articles/filter-preview`
- `GET /api/v1/articles`
- `GET /api/v1/articles/{article_id}`
- `PATCH /api/v1/articles/{article_id}/state`
- `POST /api/v1/articles/state/bulk`
- `GET /api/v1/navigation`
- `POST /api/v1/imports/opml`

## Queue/Scheduler Status

- Implemented:
  - Redis/RQ queue wiring (`src/sift/tasks/queueing.py`)
  - Ingest job wrapper (`src/sift/tasks/jobs.py`)
  - Scheduler loop that enqueues due feeds by `fetch_interval_minutes`
  - Worker process consuming ingest queue
- Config controls:
  - `SIFT_INGEST_QUEUE_NAME`
  - `SIFT_SCHEDULER_POLL_INTERVAL_SECONDS`
  - `SIFT_SCHEDULER_BATCH_SIZE`
- Dedupe guard:
  - Scheduler uses RQ-compatible stable job IDs (`ingest-<feed_id>`) for dedupe.
  - Legacy `ingest:<feed_id>` IDs are still checked for upgrade-safe dedupe behavior.

## Current Implementation Status

- Authentication:
  - local provider implemented (`auth_identities.provider = "local"`)
  - Argon2 password hashing
  - cookie sessions backed by `user_sessions`
  - schema ready for external providers (Google/Azure/Apple/OIDC)
  - OIDC provider implementation is intentionally deferred; keep schema/provider abstractions ready.
- Feed and article APIs now require authenticated sessions.
- Feed ownership is tracked via `feeds.owner_id`.
- Current limitation: feed URL is globally unique until shared-feed/subscription model is revisited.
- Feed ingestion pipeline exists:
  - fetch RSS/Atom
  - parse entries
  - store raw entry payload
  - create normalized article
  - run plugin ingest hook
- Initial dedupe exists at feed+source-id level.
- Keyword include/exclude preview exists via API.
- OPML import endpoint exists with per-user dedupe/import report (`POST /api/v1/imports/opml`).
- Persisted ingest rules are implemented and enforced during ingestion.
- Keyword streams are implemented with persisted definitions and matched article views.
- Stream classifier foundation is implemented (rules/classifier/hybrid modes + plugin confidence threshold).
- Cross-feed canonical dedup foundation is implemented (normalized URL + content fingerprint + duplicate linking/confidence).
- Scheduler and worker orchestration are now implemented for recurring ingestion.
- Feed folders are implemented (per-user folders + feed-to-folder assignment endpoint).
- Reader-first frontend workspace is implemented:
  - `/app` authenticated React + MUI 3-pane shell (tree/list/reader)
  - frontend source: `frontend/` (Vite + TypeScript + TanStack Router/Query)
  - build output: `frontend/dist`
  - Light/dark theme toggle with local persistence
  - Compact/comfortable density toggle (compact default)
  - Core keyboard shortcuts: `j/k`, `o`, `m`, `s`, `/`
  - Frontend owns routes (`/app`, `/login`, `/register`, `/account`) and talks to backend through REST APIs only.
- Settings hub + unified UI preferences are implemented:
  - `/account` now hosts appearance and reading/layout controls plus account summary
  - unified browser-local preferences model for `themeMode`, `themePreset`, `density`, and `navPreset`
  - workspace navigation preset now reads from app-level settings state
  - duplicate inline nav preset controls were removed from workspace navigation
  - settings toggle groups support keyboard arrow/home/end selection and explicit focus-visible states
  - settings include reset-to-defaults for UI preferences
  - preset-aware interaction tokens are tuned across rail/nav/list/reader surfaces
  - preset-aware base surfaces and MUI palette tokens are aligned per preset (light + dark)
  - targeted `/account` route tests cover interaction, accessibility labels, and preference persistence
- Monitoring feed management v1 is implemented:
  - `/account/monitoring` route for stream-backed monitoring definition CRUD
  - settings entry point (`Manage monitoring feeds`) from `/account`
  - optional backfill action entry point with explicit unavailable-state feedback when endpoint is not present
  - workspace explainability labels for matched monitoring streams in article list and reader
- Monitoring search language v1 is implemented:
  - backend parser/evaluator for `AND`/`OR`/`NOT`, parentheses, quoted phrases, suffix wildcard, and fuzzy tokens
  - stream expression persistence via `keyword_streams.match_query`
  - ingest-time stream matching evaluates saved expression query
  - article listing search supports advanced query syntax with validation errors for invalid expressions
  - monitoring feed editor supports creating/updating `match_query`
- Development seed bootstrap is implemented:
  - creates default local user when enabled
  - imports OPML feed folders/feeds
  - maps Inoreader monitoring feeds to keyword streams
  - personal OPML should live in `dev-data/local-seed.opml` (gitignored)
  - keep only sanitized seed sample committed (`dev-data/public-sample.opml`)

## Next Delivery Sequence

1. Add stream-level ranking and prioritization controls.
2. Add classifier run persistence and model/version tracking.
3. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
4. Add scheduler and ingestion observability (metrics, latency, failures) after core content features.

## Next UI Slice (Prioritized)

1. Monitoring feed management v1 was completed on 2026-02-16.
2. Monitoring search language v1 was completed on 2026-02-16.
3. Next UI-focused deferred follow-up is monitoring feed management v2:
   - regex/plugin matcher expansion
   - historical backfill execution path
   - richer match explainability

## Deferred

1. Add OIDC providers (Google first, then Azure/Apple) after core stream/rule/UI features stabilize.

## Feature Notes

- Keyword streams:
  - many streams per user should be supported
  - stream definitions should be saved and queryable like feeds
  - stream membership should eventually support both deterministic rules and classifier outputs
  - matcher baseline includes boolean query language (`AND`/`OR`/`NOT`) with phrases/grouping, suffix wildcard, and fuzzy tokens
- Classifier plugin direction:
  - implement as plugin hooks, not hard-coded core logic
  - support provider/model versioning, score/confidence, and failure isolation
- Feed folders direction:
  - add folder object per user
  - support OPML folder mapping on import
  - allow unfiled feeds as a default state
- Vector database direction:
  - keep vector storage behind plugin boundaries
  - start with pluggable providers (e.g., pgvector, Qdrant, Weaviate)
  - use for semantic matching/classification plugins, not as a hard dependency of core ingestion

## Planning Workflow For Future Sessions

1. Read `AGENTS.md`, `docs/backlog.md`, and `docs/session-notes.md`.
2. Confirm or update the next 3-5 priority steps.
3. Review newly captured long-horizon ideas and record/normalize them in `docs/backlog.md`.
4. Implement one vertical slice fully (code + tests + docs update).
5. End each session by updating:
   - `docs/session-notes.md` with verification results and next priorities.
   - `docs/architecture.md` if architecture changed.
   - `docs/backlog.md` when backlog status/priorities change.

## Backlog Governance

- Any long-horizon idea captured during sessions must be reviewed and added to `docs/backlog.md`.
- Avoid keeping durable backlog items only in `docs/session-notes.md`; session notes are log/history, backlog is planning source of truth.

## Where to Store Future Knowledge

- Stable constraints/instructions: `AGENTS.md`.
- Design/architecture decisions and tradeoffs: `docs/architecture.md`.
- Iteration log (what changed, why, what is next): `docs/session-notes.md`.
- Backlog source of truth (done/next/deferred): `docs/backlog.md`.
