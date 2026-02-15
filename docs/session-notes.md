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

### Workspace Nav/Visual Polish v2

- Implemented reliable folder interaction split in navigation:
  - row click now selects folder scope only
  - chevron click toggles expansion only (single-click behavior)
- Added folder controls:
  - `Expand all`
  - `Collapse all`
  - folder expansion state persisted in localStorage (`NAV_FOLDERS_EXPANDED_KEY`)
- Added feed icons in folder/feed tree:
  - favicon URL derived from feed `site_url` or `url`
  - graceful fallback to deterministic initial avatar if favicon load fails
- Applied softer visual tuning in workspace styles:
  - lower-contrast borders/backgrounds
  - calmer selected/hover states
  - improved nav/feed row softness and spacing
- Added/updated tests:
  - `frontend/src/features/workspace/lib/feedIcons.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Workspace Nav IA + Readability Polish v3

- Navigation IA updates:
  - moved `Monitoring feeds` to a standalone section above `Folders`
  - kept stream routing semantics unchanged (`scope_type="stream"`)
  - added section-level monitoring collapse/expand toggle with persisted browser-local state
- Density and icon polish:
  - reduced feed icon scale (compact-first)
  - reduced nav row/action visual weight and tightened row spacing
  - kept favicon fallback behavior for feed icons
- Reader readability updates:
  - adopted paper-editorial default in light mode (warm paper background + dark neutral text)
  - switched frontend typography defaults to `IBM Plex Sans` (UI) and `Source Serif 4` (reader body)
  - tuned reader line length, line-height, and paragraph rhythm for long-form scanning
- Added/updated tests:
  - `frontend/src/entities/navigation/model.test.ts`
  - `frontend/src/features/workspace/lib/navState.test.ts`
  - `frontend/src/features/workspace/components/NavigationPane.test.tsx`
  - `frontend/src/features/workspace/components/ReaderPane.test.tsx`

### Workspace UX Polish v4

- Added desktop pane resizing across both split boundaries:
  - navigation ↔ article list
  - article list ↔ reader
  - widths persisted in browser-local storage (`PANE_LAYOUT_KEY`)
- Added keyboard-accessible separators (`role="separator"`) with arrow/home/end controls.
- Updated monitoring header control from subtle icon-only toggle to visible labeled action (`Collapse` / `Expand`).
- Added slim workspace top bar with icon controls for:
  - dark/light mode toggle
  - settings navigation (`/account`)
- Removed density control from navigation/feed pane toolbar (to live on settings page later).
- Updated reader mark-read behavior:
  - when toggling unread -> read, selection now auto-advances to next article after mutation success
  - mark-unread does not auto-advance
- Stability improvement:
  - selected article id now falls back to first visible row when current id no longer exists in filtered results.
- Added/updated tests:
  - `frontend/src/features/workspace/lib/paneLayout.test.ts`
  - `frontend/src/features/workspace/hooks/usePaneResizing.test.tsx`
  - `frontend/src/features/workspace/lib/readActions.test.ts`
  - `frontend/src/entities/article/model.test.ts`
  - updated `frontend/src/features/workspace/components/NavigationPane.test.tsx`

### Frontend Planning Backlog (Paused)

- Session paused by user after theme/navigation polish on branch `feat/folder-nav-polish`.
- Resume plan for the next UI pass:
  1. Stabilize visual defaults:
     - keep `balanced` as default nav preset
     - keep `tight`/`airy` as optional variants, move the settings for this to a settings menu
  2. Folder panel final pass:
     - finalize row height, indent depth, and unread-count contrast values
     - verify truncation and menu discoverability at narrower widths
  3. Nav + list visual harmony:
     - align article list hover/selected/read states with softened pistachio light theme
     - keep reader pane styling unchanged
  4. Settings consolidation:
     - move display controls (nav preset/theme/density) into settings surface
     - keep quick theme toggle in top bar
  5. Wrap-up and merge readiness:
     - rerun `lint`, `typecheck`, `test`, `build`
     - open PR from `feat/folder-nav-polish` when approved
