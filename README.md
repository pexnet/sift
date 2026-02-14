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
4. Run API and web app:
   - `uv run uvicorn sift.main:app --reload`
5. Open:
   - `http://127.0.0.1:8000`

## Dev Commands

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Tests: `uv run pytest`
- Type check: `uv run mypy src`

## Docker (App + Worker + Scheduler + Postgres + Redis)

- `docker compose up --build`

## Plugin Direction

Plugins should implement the `ArticlePlugin` protocol in `src/sift/plugins/base.py`.
Configured plugin paths are loaded from `SIFT_PLUGIN_PATHS` in `.env`.

## Long-Term Project Memory

- Session-specific notes: `docs/session-notes.md`
- Architectural decisions: `docs/architecture.md`
- Codex run instructions and conventions: `AGENTS.md`

