# Release Cycle Guide

## Branching Model

Sift uses a light GitFlow model:

1. `develop` is the default integration branch.
2. `main` is the protected release branch.
3. Feature work:
   - branch from `develop` as `feature/*`
   - open PR into `develop`
4. Release flow:
   - open PR from `develop` into `main`
   - merge with merge-commit strategy
5. Hotfix flow:
   - branch from `main` as `hotfix/*`
   - PR into `main` with `release:patch`
   - back-merge into `develop`

## Release Label Contract

PRs into `main` must include exactly one release label:

- `release:major`
- `release:minor`
- `release:patch`

Optional non-release label for other branches:

- `release:none`

## CI/CD Workflow Map

1. `ci-fast` (`.github/workflows/ci-fast.yml`):
   - trigger: PRs targeting `develop`
   - backend: Ruff lint/format-check, MyPy, Pytest
   - frontend: Prettier check, lint, typecheck, tests
   - security: dependency review
2. `release-readiness` (`.github/workflows/release-readiness.yml`):
   - trigger: PRs targeting `main`
   - validates required release label
   - runs full backend/frontend checks
   - runs Trivy filesystem gate (HIGH/CRITICAL)
3. `release-main` (`.github/workflows/release-main.yml`):
   - trigger: push to `main`
   - computes SemVer tag from release label
   - builds/scans/publishes multi-arch images to GHCR
   - creates GitHub Release
4. `codeql` (`.github/workflows/codeql.yml`):
   - trigger: PR/push for `develop` and `main`, plus weekly schedule
5. Dependabot (`.github/dependabot.yml`):
   - weekly updates for actions, Python, and frontend npm deps

## Versioning Rules

1. Tag format: `vX.Y.Z`.
2. Source of truth: latest existing release tag.
3. Bump source: release label on merged PR into `main`.
4. Bootstrap behavior:
   - if no prior tag exists, release workflow initializes with `v0.1.0`.

## Container Release Artifacts

Published on each `main` release:

- `ghcr.io/pexnet/sift-backend:vX.Y.Z`
- `ghcr.io/pexnet/sift-backend:latest`
- `ghcr.io/pexnet/sift-frontend:vX.Y.Z`
- `ghcr.io/pexnet/sift-frontend:latest`

Platforms:

- `linux/amd64`
- `linux/arm64`

## Upgrade Path

Use release compose deployment:

```bash
export SIFT_VERSION=vX.Y.Z
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

Use `latest` only for non-deterministic environments; pin explicit tags for predictable rollouts.

## Required GitHub Repository Settings (Manual)

Apply these in GitHub Settings:

1. Default branch:
   - set default branch to `develop`.
2. Branch protection / ruleset for `develop`:
   - require PR
   - block direct pushes
   - require up-to-date branch
   - require `ci-fast` check
3. Branch protection / ruleset for `main`:
   - require PR
   - block direct pushes
   - require up-to-date branch
   - require at least one approval
   - require `release-readiness` check
   - require `codeql` check(s)
4. Labels:
   - create `release:major`, `release:minor`, `release:patch`, `release:none`
