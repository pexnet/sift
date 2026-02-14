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

## Working Agreements

- Prefer modular monolith architecture for MVP.
- Avoid premature microservices; isolate via interfaces first.
- All major changes should update:
  - `docs/architecture.md` for architecture-impacting decisions.
  - `docs/session-notes.md` for decision log + next steps.

## Where to Store Future Knowledge

- Stable constraints/instructions: `AGENTS.md`.
- Design/architecture decisions and tradeoffs: `docs/architecture.md`.
- Iteration log (what changed, why, what is next): `docs/session-notes.md`.

