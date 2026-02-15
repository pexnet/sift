# Sift

Sift is a self-hosted RSS and content aggregation portal focused on a reliable Python backend, extensible ingestion/classification pipelines, and a modern reader experience.

## Architecture At A Glance

- Backend: FastAPI API-only service (`/api/v1/*`) in `src/sift`.
- Frontend: standalone React + TypeScript SPA in `frontend/`.
- Integration: frontend consumes backend APIs only (no server-rendered UI coupling).

## What Sift is for

- Aggregate RSS/Atom feeds into one personal workspace.
- Organize content with folders, rules, and keyword streams.
- Support future enrichment and automation through a plugin-ready architecture.

## Documentation

- [Getting started](docs/getting-started.md) — local setup and first run.
- [Development guide](docs/development.md) — day-to-day developer workflow, tooling, and notes.
- [Deployment guide](docs/deployment.md) — containerized runtime profiles and service topology.
- [Architecture](docs/architecture.md) — system design and current/target architecture.
- [Session notes](docs/session-notes.md) — change log and near-term priorities.
