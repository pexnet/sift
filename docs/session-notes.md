# Session Notes

## 2026-02-14

- Created initial project scaffold with FastAPI + Jinja2 + HTMX.
- Added SQLAlchemy async setup and baseline models.
- Added plugin protocol and dynamic plugin loader.
- Added worker/scheduler stubs for queue-based processing.
- Standardized tooling around uv + Ruff + Pytest + Mypy.
- Ruff line width set to 120.

## Next Iteration Candidates

1. Add Alembic and first migration.
2. Build feed ingestion service (RSS/Atom fetch + parse).
3. Add initial auth model and subscription ownership constraints.
4. Add dedup and filtering pipeline skeleton.

