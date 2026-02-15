# Session Notes

## 2026-02-15

### Architecture Baseline (Current)

- Backend is API-only FastAPI (`/api/v1/*`) and does not serve frontend pages or static bundles.
- Frontend is a standalone React + TypeScript app in `frontend/`.
- Frontend routes (`/app`, `/login`, `/register`, `/account`) are owned by the SPA runtime.
- Frontend/backend integration is API-only via REST endpoints.

### Implemented This Session

- Removed backend web delivery package and route surface (`src/sift/web/*`).
- Added CORS configuration in backend settings and middleware wiring in `src/sift/main.py`.
- Added API-only regression test: `tests/test_api_only_surface.py`.
- Set frontend build output to `frontend/dist`.
- Added frontend API base URL support through `VITE_API_BASE_URL`.
- Standardized docs (`AGENTS.md`, architecture, getting-started, development, deployment) to the API-only + standalone SPA model.
- Updated Dev Container stack to include frontend service and default port `5173`.
- Updated root `docker-compose.yml` to start full local stack including frontend dev server (`http://localhost:5173`).

### Verification

- Frontend:
  - `pnpm --dir frontend run gen:openapi`
  - `pnpm --dir frontend run lint`
  - `pnpm --dir frontend run typecheck`
  - `pnpm --dir frontend run test`
  - `pnpm --dir frontend run build`
- Backend:
  - `python -m ruff check src tests`
  - `python -m mypy src`
  - `python -m pytest`

### Current Priority Plan

1. Stabilize local runtime baseline:
   - fix scheduler job-id delimiter compatibility with current RQ
   - keep dev seed idempotent without noisy duplicate-stream DB errors
2. Add stream-level ranking and prioritization controls.
3. Add classifier run persistence and model/version tracking.
4. Add vector-database integration as plugin infrastructure for embedding/matching workflows.
5. Add scheduler and ingestion observability (metrics, latency, failures) after core content features.

### Deferred

1. External OIDC provider integration (Google first, then Azure/Apple).

### Workspace UI Slice: Folder + Reader v1

- Refactored `/app` to a light, compact reader-first shell:
  - fixed app rail
  - hierarchical navigation pane
  - compact article list
  - persistent reader pane
- Removed dashboard cards from the `/app` workspace route.
- Added hierarchical navigation view model mapping in `frontend/src/entities/navigation/model.ts`:
  - system, folder, feed, and stream scope mapping
  - unified scope label resolution for current URL scope
- Added folder management and feed assignment flows using existing APIs:
  - create/rename/delete folder
  - move feed to folder / unfiled
  - query invalidation for navigation, folders, feeds, and articles
- Reworked article list rows for compact dense rendering with unread/saved indicators and metadata.
- Reworked reader pane with core actions (`read`, `save`, `open original`, `prev`, `next`).
- Added responsive behavior updates:
  - desktop: fixed 3-pane layout
  - tablet/mobile: collapsible navigation drawer from rail action
  - mobile: progressive list/reader panel flow with back-to-list action
- Added/updated frontend tests:
  - navigation hierarchy mapping
  - folder DTO/validation shaping
  - compact article row rendering
  - reader action wiring

### Verification (Workspace Slice)

- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run test`
- `pnpm --dir frontend run build`
- `python -m pytest tests/test_article_state_api.py tests/test_article_service.py`

### Workspace UI Modernization + Reader Formatting

- Implemented editorial-light workspace polish for `/app`:
  - updated visual tokens and spacing hierarchy for rail/nav/list/reader panes
  - improved hover/active/focus states and compact readability
  - replaced rail glyph labels with MUI icons for clearer affordances
- Implemented safe reader content rendering:
  - added `frontend/src/features/workspace/lib/readerContent.ts`
  - sanitized article markup using DOMPurify with allowlisted semantic tags
  - normalized rendered links with safe `target`/`rel` attributes
  - converted plaintext payloads into paragraph-based HTML fallback
- Updated reader component contract:
  - `ReaderPane` now renders preprocessed sanitized HTML body content
  - kept existing reader action behavior (`read/save/open/prev/next`)
- Added tests for sanitizer and reader behavior:
  - `frontend/src/features/workspace/lib/readerContent.test.ts`
  - expanded `frontend/src/features/workspace/components/ReaderPane.test.tsx`
