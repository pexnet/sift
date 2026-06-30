# Session Notes

This file is a rolling recent execution log for fast session startup.
Historical notes are archived by month under `docs/session-notes/archive/`.

## 2026-06-30 (Security Review Follow-Up: Workstream A Fixes)

### Implemented This Session

- Completed full code review deliverables:
  - `docs/code-review-2026-06-30.md`
  - `.hermes/plans/2026-06-30_code-review-fixes-and-backlog-advancement.md`
- Closed Workstream A security/CI/deploy fixes:
  - extracted shared SSRF validation utility and refactored fulltext fetch validation to use it,
  - applied SSRF validation to feed ingestion, feed creation, and discovery candidate validation,
  - replaced OPML XML parsing with `defusedxml`,
  - added 5MB feed response and OPML upload limits plus OPML nesting-depth limit,
  - redacted Redis credentials from scheduler/worker startup logs,
  - fixed `rule_service.to_out()` to use `rule.action` instead of hardcoding `drop`,
  - fixed backend Ruff formatting drift and frontend ESLint assertion errors,
  - added and verified frontend Docker/Nginx image build,
  - raised Vitest component-test timeout to stabilize full-suite jsdom/MUI runs.

### Verification

- Backend:
  - `ruff check src tests`
  - `ruff format --check src tests`
  - `mypy src/sift`
  - `python -m pytest tests/ -q` → 162 passed, 1 Starlette/httpx deprecation warning
- Frontend:
  - `npx eslint .`
  - `npx tsc --noEmit`
  - `npx vitest run` → 27 files / 112 tests passed
  - `npm run build` → pass, existing >500k chunk warning remains
- Container:
  - `docker build -t sift-frontend-test frontend/` → pass

## 2026-03-01 (Planning Review: Add SearXNG Discovery Verification Backlog Item)

### Implemented This Session

- Reviewed planning sources for consistency:
  - `AGENTS.md`
  - `docs/backlog.md`
  - `docs/backlog-history.md`
  - `docs/current-state.md`
  - `docs/architecture.md`
  - `docs/session-notes.md`
- Added explicit next-session backlog item for discovery provider verification:
  - SearXNG instance compatibility check against runtime API contract,
  - candidate public-instance validation and usable endpoint shortlist,
  - config guidance update for discovery/session testing.
- Updated `docs/current-state.md` active priorities to include the SearXNG verification pass.
- Maintained rolling-window policy by archiving the oldest entry in this file to `docs/session-notes/archive/2026-03.md`.

### Verification

- `rg -n "Discovery provider verification pass \\(SearXNG\\)|SearXNG instance compatibility" docs/backlog.md docs/current-state.md`
- `rg -n "^## 2026-03-01" docs/session-notes.md`

## 2026-03-01 (Discover Feeds v1 Final Closeout: Spec Archive + Backlog Handoff)

### Implemented This Session

- Archived discover-feeds v1 spec from active specs to completed archive:
  - moved `docs/specs/feed-recommendations-v1.md` -> `docs/specs/done/feed-recommendations-v1.md`
  - updated status metadata in archived spec to `Completed` (completed on 2026-03-01).
- Updated planning docs for completed-feature lifecycle consistency:
  - active backlog now promotes monitoring feed management v2 follow-ups as the next core platform priority,
  - discover-feeds completion moved to `docs/backlog-history.md`,
  - current-state now marks discover-feeds as completed/archived with done-spec reference.
- Updated cross-spec references to point at archived discover-feeds spec from active and completed specs.

### Verification

- `rg -n "feed-recommendations-v1.md|done/feed-recommendations-v1.md" docs AGENTS.md`
- `Get-ChildItem docs/specs`
- `Get-ChildItem docs/specs/done`

## 2026-03-01 (Discover Feeds v1 Slice 6: Recommendation Source/Evidence UI Surfacing)

### Implemented This Session

- Extended discovery recommendation cards to surface source/evidence details:
  - source-stream chips from `recommendation.sources` (with confidence labels when available),
  - recommendation evidence description rendering from `recommendation.evidence`,
  - query-variant chips aggregated from recommendation- and source-level evidence payloads.
- Added targeted frontend test coverage for source/evidence rendering in `DiscoveryWorkbench`.
- Updated planning docs to reflect discover-feeds implementation through slice 6 and narrowed remaining scope to final
  spec/archive closeout.

### Verification

- `npm --prefix frontend run test -- DiscoveryWorkbench.test.tsx WorkspacePage.test.tsx`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run build`

## 2026-03-01 (Discover Feeds v1 Slice 5: Copy-from-Monitoring Convenience Action)

### Implemented This Session

- Added discovery copy convenience API:
  - `POST /api/v1/discovery/streams/copy-from-monitoring`
  - request schema: `monitoring_stream_id` + optional target `name`
  - ownership-aware source lookup with explicit `404` when monitoring stream is missing.
- Added discovery service copy behavior:
  - loads monitoring stream criteria and creates a discovery stream via existing validated create path,
  - copies supported criteria (`match_query`, include/exclude keywords, description, active state, priority),
  - rejects copy when no discovery-compatible criteria are present.
- Added frontend copy flow in discovery settings workbench:
  - monitoring stream selector + optional discovery name field + copy action,
  - successful copy selects newly created discovery stream for immediate editing.
- Added/updated tests:
  - backend service/API copy coverage (`tests/test_discovery_service.py`, `tests/test_discovery_api.py`),
  - frontend workbench + workspace route mock updates (`DiscoveryWorkbench.test.tsx`, `WorkspacePage.test.tsx`).
- Updated planning docs for consistency:
  - `docs/backlog.md`
  - `docs/current-state.md`
  - `docs/specs/done/feed-recommendations-v1.md`

### Verification

- `.venv-ci-test\Scripts\ruff.exe check src/sift/services/discovery_service.py src/sift/api/routes/discovery.py src/sift/domain/schemas.py tests/test_discovery_service.py tests/test_discovery_api.py`
- `.venv-ci-test\Scripts\python.exe -m pytest tests/test_discovery_service.py tests/test_discovery_api.py`
- `npm --prefix frontend run test -- DiscoveryWorkbench.test.tsx WorkspacePage.test.tsx`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`

## 2026-03-01 (Planning-Doc Consistency Cleanup Pass)

### Implemented This Session

- Ran a planning-source consistency pass across:
  - `docs/backlog.md`
  - `docs/current-state.md`
  - `docs/architecture.md`
  - `docs/specs/done/feed-recommendations-v1.md`
  - `docs/specs/plugin-ui-organization-v1.md`
  - `docs/session-notes.md`
- Cleaned active backlog status so completed search-provider v1 is no longer listed as active `Next` work.
- Updated stale discovery status references (current-state and spec) to reflect implemented slices 1-4.
- Updated architecture route list to include implemented discovery settings route (`/account/discovery`).
- Enforced rolling-window policy in session notes and archived older 2026-03 entries to:
  - `docs/session-notes/archive/2026-03.md`

### Verification

- `rg -n "Core Platform Priorities|Search provider plugin v1 is completed and archived|Stream-Level Ranking" docs/backlog.md`
- `rg -n "slices 1-4 implemented|recommendation workflow hardening|discovery frontend wiring" docs/current-state.md`
- `rg -n "/account/discovery|Frontend owns routes" docs/architecture.md`
- `rg -n "Implemented slices|Remaining scope|tracks remaining closeout scope" docs/specs/done/feed-recommendations-v1.md`
- `rg -n "State: In progress|Baseline implementation is complete" docs/specs/plugin-ui-organization-v1.md`
- `rg -n "^## " docs/session-notes.md`

## Rolling Window Policy

- Keep only the most recent 3-5 session entries in this file.
- Move older entries to monthly archives in `docs/session-notes/archive/`.
- Keep each entry concise and link specs/docs rather than repeating large histories.
