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

- [Install guide](docs/install.md) — self-hosted setup from zero to first login.
- [Getting started](docs/getting-started.md) — local setup and first run.
- [Development guide](docs/development.md) — day-to-day developer workflow, tooling, and notes.
- [Deployment guide](docs/deployment.md) — containerized runtime profiles and service topology.
- [Release cycle](docs/release-cycle.md) — GitFlow, CI/CD gates, SemVer labels, and GHCR release process.
- [Architecture](docs/architecture.md) — system design and current/target architecture.
- [Session notes](docs/session-notes.md) — change log and near-term priorities.

## Quick Install

For a self-hosted install:

1. Clone repo and copy env file:
   - `git clone https://github.com/pexnet/sift.git && cd sift`
   - `cp .env.example .env` (or `Copy-Item .env.example .env` on PowerShell)
2. Set production values in `.env` (`SIFT_ENV=production`, strong DB password, CORS origin).
3. Start release stack:
   - `docker compose -f docker-compose.release.yml pull`
   - `docker compose -f docker-compose.release.yml up -d`
4. Open `http://localhost/register` and create the first user.

Full details: `docs/install.md`.

## Branch and Release Model

- `develop` is the default integration branch.
- `main` is the protected release branch.
- Releases are tag-driven (`vX.Y.Z`) and automated from merges into `main`.
- Container artifacts are published to GHCR for both backend and frontend:
  - `ghcr.io/pexnet/sift-backend:vX.Y.Z` and `:latest`
  - `ghcr.io/pexnet/sift-frontend:vX.Y.Z` and `:latest`
