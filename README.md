# Sift

Sift is a self-hosted RSS aggregation portal designed for a solid Python backend, easy extensibility, and a simple web UI.

## Stack (MVP Foundation)

- Backend: FastAPI, SQLAlchemy, Pydantic Settings
- UI: Jinja2 templates + HTMX
- Queue/Scheduling: Redis + RQ + scheduler stub
- Storage: PostgreSQL in Docker (SQLite default for local bootstrap)
- Tooling: uv, Ruff, Pytest, Mypy

## Quick Start

1. Install `uv`: <https://docs.astral.sh/uv/getting-started/installation/>
2. Create env file:
   - `copy .env.example .env`
3. Create virtual environment and sync dependencies:
   - `uv sync --dev`
4. Run migrations:
   - `uv run alembic upgrade head`
5. Run API and web app:
   - `uv run uvicorn sift.main:app --reload`
6. Open:
   - `http://127.0.0.1:8000`

## Dev Commands

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Tests: `uv run pytest`
- Type check: `uv run mypy src`
- New migration: `uv run alembic revision --autogenerate -m "your message"`
- Run worker: `uv run python -m sift.tasks.worker`
- Run scheduler: `uv run python -m sift.tasks.scheduler`

## Docker (App + Worker + Scheduler + Postgres + Redis)

- `docker compose up --build`

## Plugin Direction

Plugins should implement the `ArticlePlugin` protocol in `src/sift/plugins/base.py`.
Configured plugin paths are loaded from `SIFT_PLUGIN_PATHS` in `.env`.

## API Notes (Current)

- Register: `POST /api/v1/auth/register`
- Login: `POST /api/v1/auth/login`
- Logout: `POST /api/v1/auth/logout`
- Current user: `GET /api/v1/auth/me`
- List feeds: `GET /api/v1/feeds`
- Create feed: `POST /api/v1/feeds`
- Ingest one feed now: `POST /api/v1/feeds/{feed_id}/ingest`
- Keyword filter preview: `POST /api/v1/articles/filter-preview`

## Authentication and Identity Providers

- Local accounts use Argon2 password hashing and secure session cookies.
- Identity model is provider-aware via `auth_identities` table.
- Current provider: `local`.
- Planned providers (same user model): Google, Azure AD/Microsoft, Apple, and other OIDC-compliant providers.

## Background Processing

- Scheduler polls active feeds and enqueues due ingest jobs in Redis/RQ.
- Worker consumes queue jobs and runs feed ingestion.
- Queue and scheduler behavior are configurable through:
  - `SIFT_INGEST_QUEUE_NAME`
  - `SIFT_SCHEDULER_POLL_INTERVAL_SECONDS`
  - `SIFT_SCHEDULER_BATCH_SIZE`

## Long-Term Project Memory

- Session-specific notes: `docs/session-notes.md`
- Architectural decisions: `docs/architecture.md`
- Codex run instructions and conventions: `AGENTS.md`

