# Deployment Guide

## Runtime Topology

The standard multi-service runtime includes:
- `app` (FastAPI)
- `worker` (RQ worker)
- `scheduler` (ingest scheduler loop)
- `db` (PostgreSQL)
- `redis` (queue backend)
- `traefik` (edge/router in devcontainer profile)

See architecture details in [`docs/architecture.md`](architecture.md).

## Docker Compose

Start full stack:

- `docker compose up --build`

This profile is suitable for local production-like iteration and validates service wiring across app, queue, and scheduler.

## Dev Container Compose

Run the devcontainer service topology (without opening VS Code):

- `docker compose -f .devcontainer/docker-compose.yml up --build`

This launches the same core services used by the recommended development environment.

## Operational Notes

- Run database migrations before or during app startup.
- Keep scheduler and worker running to support recurring ingestion.
- Configure queue/scheduler behavior with:
  - `SIFT_INGEST_QUEUE_NAME`
  - `SIFT_SCHEDULER_POLL_INTERVAL_SECONDS`
  - `SIFT_SCHEDULER_BATCH_SIZE`
