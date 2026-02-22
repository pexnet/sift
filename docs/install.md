# Install Guide

This guide is for running Sift as a self-hosted system.

For day-to-day development setup, use `docs/getting-started.md` instead.

## Recommended Path (Docker + GHCR Images)

This path is the easiest way to run Sift in a stable self-hosted setup.

## Prerequisites

- Docker Engine with Docker Compose plugin (`docker compose`)
- A machine with ports `80` and `8000` available

## 1. Get the project files

```bash
git clone https://github.com/pexnet/sift.git
cd sift
```

## 2. Create runtime environment file

Copy the example file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then update `.env` for deployment. At minimum:

- `SIFT_ENV=production`
- `SIFT_DATABASE_URL=postgresql+asyncpg://sift:<strong-password>@db:5432/sift`
- `SIFT_AUTH_COOKIE_SECURE=true` (if serving over HTTPS)
- `SIFT_CORS_ALLOW_ORIGINS=["https://your-domain.example"]`
- `POSTGRES_PASSWORD=<strong-password>`

Optional image tag pin:

- `SIFT_VERSION=vX.Y.Z` for deterministic deploys
- omit `SIFT_VERSION` to use `latest`

## 3. Start Sift

```bash
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

Open:

- App: `http://localhost`
- API docs: `http://localhost:8000/docs`

## 4. Create first user

Use the register screen at:

- `http://localhost/register`

If you prefer API registration:

- `POST /api/v1/auth/register`

## 5. Verify system health

```bash
docker compose -f docker-compose.release.yml ps
curl http://localhost:8000/api/v1/health
```

## Upgrade Instructions

To upgrade to a newer release:

```bash
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

If pinning versions, update `SIFT_VERSION` in `.env` first.

## Troubleshooting

1. Port conflict on `80` or `8000`:
   - change host-side ports in `docker-compose.release.yml`
2. Frontend loads but API calls fail:
   - verify `app` container is healthy and reachable
   - check `docker compose -f docker-compose.release.yml logs app`
3. Login/session cookie issues:
   - set `SIFT_AUTH_COOKIE_SECURE=true` only when HTTPS is enabled
4. CORS errors:
   - verify `SIFT_CORS_ALLOW_ORIGINS` contains your frontend origin
