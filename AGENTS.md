# Project Agent Notes

This file stores persistent project context for future Codex sessions.

## Product Intent

- Build a self-hosted RSS/content aggregation portal.
- Prioritize backend quality and extension points.
- Keep frontend simple, sleek, and maintainable without heavy JS frameworks.

## Technical Direction (Current)

- Python backend using FastAPI.
- Database-backed ingestion pipeline with SQLAlchemy.
- Plugin-ready core for enrichment/transformation/integration use cases.
- UI with Jinja2 + HTMX.
- Tooling standards: uv + Ruff + Pytest + Mypy.
- Ruff width: 120 chars.
- Alembic is the source of truth for schema changes.

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
- `POST /api/v1/articles/filter-preview`
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
  - Scheduler uses stable job IDs (`ingest:<feed_id>`) and avoids duplicate active jobs.

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
- Scheduler and worker orchestration are now implemented for recurring ingestion.

## Next Delivery Sequence

1. Extend streams with classifier plugins (LLM/ML/rule classifiers with confidence + reasoning).
2. Add cross-feed canonical dedup improvements and scoring.
3. Add scheduler and ingestion observability (metrics, latency, failures).
4. Add stream-level ranking and prioritization controls.
5. Add OIDC providers (Google first, then Azure/Apple) after core stream/rule features stabilize.

## Feature Notes

- Keyword streams:
  - many streams per user should be supported
  - stream definitions should be saved and queryable like feeds
  - stream membership should eventually support both deterministic rules and classifier outputs
- Classifier plugin direction:
  - implement as plugin hooks, not hard-coded core logic
  - support provider/model versioning, score/confidence, and failure isolation

## Planning Workflow For Future Sessions

1. Read `AGENTS.md` and `docs/session-notes.md`.
2. Confirm or update the next 3-5 priority steps.
3. Implement one vertical slice fully (code + tests + docs update).
4. End each session by updating:
   - `docs/session-notes.md` with verification results and next priorities.
   - `docs/architecture.md` if architecture changed.

## Where to Store Future Knowledge

- Stable constraints/instructions: `AGENTS.md`.
- Design/architecture decisions and tradeoffs: `docs/architecture.md`.
- Iteration log (what changed, why, what is next): `docs/session-notes.md`.

