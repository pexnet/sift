# Sift Observability Stack (VictoriaMetrics + VictoriaLogs)

This folder provides a full local observability stack for Sift runtime telemetry:

- Metrics storage/query: VictoriaMetrics single-node
- Metrics scraping/forwarding: `vmagent`
- Logs storage/query: VictoriaLogs
- Log shipping: Vector (`docker_logs` source from Sift containers)

The stack is designed to run alongside the existing root `docker-compose.yml`.

## What Gets Collected

1. Metrics from:
   - `app:8000/metrics`
   - `scheduler:9101/metrics`
   - `worker:9102/metrics`
2. Structured logs from Sift containers:
   - `app`
   - `scheduler`
   - `worker`

## Prerequisites

1. Docker Engine + Docker Compose v2
2. Run commands from repository root (`sift/`)

## Start (Full Stack + Observability)

```bash
docker compose \
  -f docker-compose.yml \
  -f ops/observability/docker-compose.observability.yml \
  up -d --build
```

If Sift is already running and you only want observability services:

```bash
docker compose \
  -f docker-compose.yml \
  -f ops/observability/docker-compose.observability.yml \
  up -d victoriametrics victorialogs vmagent vector
```

## Stop

```bash
docker compose \
  -f docker-compose.yml \
  -f ops/observability/docker-compose.observability.yml \
  down
```

To remove observability volumes too:

```bash
docker compose \
  -f docker-compose.yml \
  -f ops/observability/docker-compose.observability.yml \
  down -v
```

## Endpoints

- VictoriaMetrics API/UI: `http://localhost:8428`
- VictoriaLogs API/UI: `http://localhost:9428`
- vmagent status/targets: `http://localhost:8429`
- Vector API: `http://localhost:8686`

## Quick Verification

1. Check `vmagent` sees scrape targets:

```bash
curl http://localhost:8429/targets
```

2. Check metric names exist in VictoriaMetrics:

```bash
curl "http://localhost:8428/api/v1/label/__name__/values" | jq
```

3. Generate traffic (e.g. `GET /api/v1/health`) and check logs are being ingested:

```bash
curl -X POST "http://localhost:9428/select/logsql/query" \
  -d "query=service:*" \
  -d "limit=20"
```

## Files

- Compose overlay: `ops/observability/docker-compose.observability.yml`
- vmagent scrape config: `ops/observability/vmagent/prometheus.yml`
- Vector pipeline config: `ops/observability/vector/vector.yaml`

## Notes

1. This stack is local-first and intentionally simple.
2. For production, deploy observability services separately from app runtime and use persistent storage/backup policies.
3. Adjust scrape intervals, retention, and resource limits for your environment.
