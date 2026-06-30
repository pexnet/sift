# Codebase Review — 2026-06-30

Full manual review of the Sift codebase (backend + frontend).

## Baseline Health

| Check | Result |
|-------|--------|
| ruff check (backend) | PASS |
| ruff format --check (backend) | 15 files need formatting |
| mypy (backend, 68 files) | PASS — no issues |
| pytest (backend) | 146 passed, 1 warning |
| tsc --noEmit (frontend) | PASS — no errors |
| eslint (frontend) | 6 errors (unnecessary type assertions) |
| vitest (frontend) | 109 passed, 3 failed (timeouts in MonitoringFeedsPage) |
| vite build (frontend) | PASS — chunk size warning (852 KB JS) |
| Backend coverage | 79% overall (5481 stmts, 1161 missing) |

### Pre-existing warnings

- Starlette deprecation: `Using httpx with starlette.testclient is deprecated; install httpx2 instead.` (pytest warning)
- Vite chunk warning: `dist/assets/index-DEOK7R47.js 852.12 kB` — over 500KB limit, needs code-splitting

---

## CRITICAL

### [C1] SSRF: ingestion service fetches arbitrary feed URLs without validation

**File:** `src/sift/services/ingestion_service.py:178-179`

The ingestion service creates an `httpx.AsyncClient` and fetches `feed.url` directly with no URL validation. A user can add a feed with an internal IP or localhost URL, and the server will fetch it, exposing internal services.

The `article_fulltext_service.py` already has proper SSRF protection (`_validate_fetch_url`, `_assert_public_host`, `_assert_public_ip` at lines 167-201), but the same protection is NOT applied to feed ingestion.

**Impact:** Any authenticated user can make the server issue HTTP requests to internal addresses (e.g., `http://169.254.169.254/` for cloud metadata, `http://localhost:6379/` for Redis, `http://10.0.0.1/admin`).

**Fix:** Extract the SSRF validation from `article_fulltext_service.py` into a shared utility (e.g., `src/sift/services/url_validation.py`) and apply it in `ingestion_service.py` before the `client.get(feed.url)` call at line 179. Also validate the feed URL at creation time in `feed_service.create_feed()`. Additionally, since `follow_redirects=True`, validate the **final** URL after redirects as well, not just the initial URL.

### [C2] SSRF: discovery service candidate validation fetches arbitrary URLs

**File:** `src/sift/services/discovery_service.py:978-980, 1040, 1058`

The `_validate_candidates` method uses `httpx.AsyncClient(follow_redirects=True)` with only a scheme/netloc check in `_normalize_candidate_url` — no private IP/loopback/metadata-endpoint blocking. Candidates come from external search providers (SearXNG, Brave), which could return internal URLs. The HTML autodiscovery parser (`_discover_feed_links_from_html`) also follows arbitrary `<link>` hrefs.

**Impact:** A compromised or malicious search provider result could cause the server to fetch internal endpoints during discovery candidate validation.

**Fix:** Apply the same SSRF validation utility (shared with C1) to every URL before issuing `client.get(url)`, including autodiscovered hrefs after `urljoin`.

### [C3] XXE / entity expansion risk in OPML parser

**File:** `src/sift/services/opml_service.py:4, 75`

`parse_opml` uses `xml.etree.ElementTree.fromstring(content)` which is vulnerable to entity expansion attacks ("billion laughs"/"quadratic blowup") on untrusted OPML uploads. The OPML content is user-uploaded via `/api/v1/imports/opml`.

**Fix:** Use `defusedxml.ElementTree` instead of `xml.etree.ElementTree`. Add `defusedxml` to dependencies.

---

## HIGH

### [H1] Insecure default: auth_cookie_secure defaults to False

**File:** `src/sift/config.py` (auth_cookie_secure setting)

The session cookie `secure` flag defaults to `False`. In production over HTTPS, this means the cookie can be transmitted over plain HTTP if the user accidentally navigates to the HTTP variant, exposing the session token.

**Fix:** Default `auth_cookie_secure` to `True` when `env != "development"`, or make it a required production setting. At minimum, document that it must be set to `True` in production deployment.

### [H2] CORS allows credentials with wildcard methods and headers

**File:** `src/sift/config.py:31-32`

```python
cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])
```

Combined with `cors_allow_credentials: True`, this is a permissive CORS configuration. While origins are restricted to localhost (development), if this defaults to production without changing origins, any misconfigured origin list is dangerous with wildcard methods + credentials.

**Fix:** Replace `["*"]` with explicit method/header lists in production. Add a startup warning if credentials are enabled with wildcard methods/headers and env is not development.

### [H3] Advanced search loads all matching articles into memory

**File:** `src/sift/services/article_service.py:213-226`

When `requires_advanced_search(q)` is true (boolean/phrase/wildcard/fuzzy queries), the code loads ALL matching rows from the database with no limit, then filters in Python:

```python
all_rows_result = await session.execute(
    base_query.where(*filters).order_by(*_sorting_clause(...))
)
filtered_rows = [row for row in all_rows_result.all() if parsed_query.matches(...)]
```

This is a memory and performance bomb for large article sets. A user with 50K articles and a broad query like `"the"` would load all 50K rows into memory.

**Fix:** For advanced search, add a DB-level pre-filter where possible (e.g., LIKE for wildcard prefixes), or cap the scan with a large LIMIT (e.g., 10000) and report truncated results. The backlog already notes "Advanced Search Query Acceleration" as deferred item #6 — this should be elevated to HIGH priority given the memory risk.

### [H4] mark_scope_as_read also loads all article IDs into memory

**File:** `src/sift/services/article_service.py:442-452`

Similar to H3, `mark_scope_as_read` with advanced search loads all matching article IDs into memory before passing them to `bulk_patch_state`. For a broad query matching tens of thousands of articles, this creates a large in-memory list and then issues a single `IN (...)` query with all those IDs.

**Fix:** Batch the update in chunks (e.g., 500 IDs per `IN` clause), or use a subquery-based UPDATE for the non-advanced-search path.

### [H5] Unbounded OPML import: no file size limit, no recursion depth limit

**File:** `src/sift/api/routes/imports.py:26` and `src/sift/services/opml_service.py:73-90`

The import endpoint reads the entire uploaded file into memory (`await file.read()`) with no size limit. A malicious OPML with millions of nested `<outline>` elements could exhaust memory. Also, `_extract_entries` recurses with no depth limit, risking stack overflow on deeply nested XML.

**Fix:** Add a file size check (e.g., `if len(content) > 5_000_000: raise 413`), and add a recursion depth limit to `_extract_entries` (e.g., `max_depth=100`).

### [H6] Ingestion service has no response size limit

**File:** `src/sift/services/ingestion_service.py:178, 228`

`httpx.AsyncClient` downloads the full response body into memory with no size cap. A malicious feed URL could serve a 10GB response, causing OOM. `feedparser.parse(response.content)` then parses it all. Unlike `article_fulltext_service.py` which has `_MAX_RESPONSE_BYTES` (2MB), ingestion has no such guard.

**Fix:** Use streaming or check `Content-Length` and abort if too large (e.g., 5MB for feeds).

### [H7] SSRF TOCTOU race (DNS rebinding) in fulltext fetch

**File:** `src/sift/services/article_fulltext_service.py:167-196`

`_validate_fetch_url` resolves the hostname via `socket.getaddrinfo` and validates IPs, but then `_fetch_source_page` makes a separate `httpx` call that resolves DNS again. Between validation and fetch, DNS could change (DNS rebinding), bypassing the private-IP check. Also, `follow_redirects=True` means redirected targets are not re-validated.

**Fix:** Resolve the IP in `_validate_fetch_url` and connect to the IP directly with Host header, or use a custom httpx transport that resolves and validates each connection IP including redirects.

### [H8] OPML import leaks whether another user owns a feed URL

**File:** `src/sift/services/opml_service.py:138, 155-164`

The `existing_query` at line 138 checks `Feed.url.in_([...])` without filtering by `owner_id`, finding feeds owned by other users. The import then reports `"Feed URL already exists under another account"`, leaking that another user has subscribed to that URL.

**Fix:** Filter the existing query by `owner_id` first. If the URL exists globally but not for this user, return a generic "Feed URL already exists" without revealing account ownership.

---

## MEDIUM

### [M1] 15 files need ruff format — CI format check will fail

**Files:** `discovery_service.py`, `search_service.py`, and 5 test files

`ruff format --check` reports 15 files that need reformatting. This will fail the CI format check gate.

**Fix:** Run `ruff format src tests` to fix all formatting.

### [M2] Frontend: 6 ESLint errors (unnecessary type assertions)

**Files:**
- `frontend/src/entities/article/model.ts:114, 148`
- `frontend/src/entities/navigation/model.ts:113`
- `frontend/src/entities/user/model.ts:16`
- `frontend/src/features/feed-health/routes/FeedHealthPage.tsx:248`
- `frontend/src/features/monitoring/routes/MonitoringFeedsPage.tsx:569`

All are `@typescript-eslint/no-unnecessary-type-assertion` — type assertions that don't change the type. CI lint gate will fail.

**Fix:** Run `npx eslint . --fix` or manually remove the unnecessary `as` assertions.

### [M3] Frontend: 3 test failures (timeouts) in MonitoringFeedsPage

**File:** `frontend/src/features/monitoring/routes/MonitoringFeedsPage.test.tsx`

3 tests time out after 5000ms. These are pre-existing failures — the test suite reports `3 failed | 109 passed`.

**Fix:** Investigate the test timeouts — likely async act warnings or missing mock setup causing the test to hang waiting for a condition that never resolves.

### [M4] Frontend: JS bundle is 852 KB — exceeds 500KB chunk size limit

**File:** `frontend/` (vite build output)

Vite warns: `dist/assets/index-DEOK7R47.js 852.12 kB │ gzip: 259.26 kB`. The entire app is in a single chunk.

**Fix:** Configure `build.rollupOptions.output.manualChunks` to split vendor code (MUI, TanStack, React) into separate chunks. Or use dynamic imports for feature routes (discovery, monitoring, feed-health, settings) since they're not needed on initial load.

### [M5] Feed ingestion: httpx client not closed on exception in some paths

**File:** `src/sift/services/ingestion_service.py:177-195`

The `httpx.AsyncClient` is used with `async with` which is correct, but the error handling path commits the session and returns before the `async with` block exits cleanly. While Python's `async with` handles this, the pattern of committing inside the `except` block (line 185) before the response is fully processed is fragile.

**Fix:** This is minor — the `async with` ensures cleanup. But consider restructuring to avoid committing in the except block.

### [M6] Dockerfile copies docs/ and AGENTS.md into production image

**File:** `Dockerfile:12-13`

```
COPY docs ./docs
COPY AGENTS.md ./
```

These are not needed at runtime and increase the image size unnecessarily.

**Fix:** Remove `COPY docs ./docs` and `COPY AGENTS.md ./` from the production Dockerfile.

### [M7] No frontend Dockerfile — CI release pipeline can't build frontend image

**File:** `frontend/` (missing Dockerfile)

The architecture docs mention GHCR image publish for `sift-frontend`, but there's no `frontend/Dockerfile`. The CI release pipeline likely can't build the frontend image.

**Fix:** Create `frontend/Dockerfile` (multi-stage: node build → nginx serve).

### [M8] User model inconsistency: user_id stored as str in some tables, UUID in others

**File:** `src/sift/db/models.py`

- `Subscription.user_id: Mapped[str]` (line 56) — uses `String(255)` not UUID
- `ArticleState.user_id: Mapped[str]` (line 97) — uses `String(255)` not UUID
- But `FeedFolder.user_id`, `Feed.owner_id`, `IngestRule.user_id`, etc. use `UUID(as_uuid=True)`

This inconsistency means some queries use `str(user_id)` and others use `user_id` directly. It works because SQLAlchemy compares the string representation, but it's a latent bug if the comparison ever changes.

**Fix:** Standardize on UUID for all user_id foreign keys. This requires migrations to alter column types.

### [M9] No rate limiting on auth endpoints

**File:** `src/sift/api/routes/auth.py:60-83` (login endpoint)

The login endpoint has no rate limiting. An attacker can brute-force passwords without any throttling.

**Fix:** Add rate limiting (e.g., `slowapi` or a simple in-memory counter) on `/auth/login` and `/auth/register`. The backlog already mentions auth improvements but doesn't explicitly call out rate limiting.

### [M10] rule_service.to_out hardcodes action="drop" instead of using rule.action

**File:** `src/sift/services/rule_service.py:239`

```python
def to_out(self, rule: IngestRule) -> IngestRuleOut:
    return IngestRuleOut(
        ...
        action="drop",  # BUG: should be rule.action
        ...
    )
```

The `to_out` method always returns `action="drop"` ignoring the actual `rule.action` value. If future rule actions are added, this will silently return wrong data.

**Fix:** Change to `action=rule.action`.

### [M11] Feed health service: full table scan + in-memory pagination

**File:** `src/sift/services/feed_health_service.py:69-127`

`list_feed_health` loads ALL feeds for the user, computes staleness/error for each in Python, then does in-memory slicing (`items[offset : offset + limit]`). For a user with 10,000 feeds, this loads all 10k rows every request. The `_summary` method loads all feeds again and computes counts in Python — should be a SQL aggregate.

**Fix:** Push filtering (stale_only, error_only) into SQL where possible. Apply LIMIT/OFFSET at the SQL level before loading into memory. Use SQL `COUNT(*) FILTER (WHERE ...)` for the summary.

### [M12] Scheduler/worker log redis_url in plaintext (credential leak)

**File:** `src/sift/tasks/scheduler.py:210`, `src/sift/tasks/worker.py:33`

`"redis_url": settings.redis_url` is logged on startup. Redis URLs often contain passwords (`redis://:password@host:port`). This exposes credentials in logs.

**Fix:** Redact the password from the URL before logging.

### [M13] Stream backfill: non-atomic delete-then-insert + unbounded article scan

**File:** `src/sift/services/stream_service.py:884-892, 843-858`

`run_stream_backfill` deletes all existing `KeywordStreamMatch` rows for the stream, then inserts new ones. If the re-scan produces fewer matches, the user's existing matches are permanently lost. The entire article table for the user is scanned with no LIMIT — unbounded for users with many articles.

**Fix:** Add a limit to the article scan. Consider keeping existing matches and only adding/removing diffs, or document that backfill is destructive.

---

## LOW

### [L1] Module-level singleton pattern for services

**Files:** All service files (e.g., `article_service = ArticleService()`)

All services are instantiated as module-level singletons. This works but makes testing harder and creates implicit coupling. The services don't hold state, so it's not dangerous, but it's an anti-pattern.

**Fix:** Consider using FastAPI dependency injection for services instead of module-level singletons. Low priority since it works correctly.

### [L2] `search_provider_noop.py` has 0% test coverage

**File:** `src/sift/plugins/builtin/search_provider_noop.py`

This plugin has no test coverage. While it's a noop, it should have at least a smoke test.

### [L3] worker.py has 0% test coverage

**File:** `src/sift/tasks/worker.py`

The worker entrypoint has no tests. It's a thin wrapper, but the `main()` function should have at least an import/smoke test.

### [L4] scheduler.py has only 40% coverage

**File:** `src/sift/tasks/scheduler.py`

The scheduler loop (`run_scheduler_loop`, `main`) and queue metric functions are untested. The `_is_feed_due` and `enqueue_due_feeds` logic is tested, but the full loop and metrics server startup are not.

### [L5] `mypy` override for feedparser suppresses missing import errors

**File:** `pyproject.toml:74-76`

```toml
[[tool.mypy.overrides]]
module = ["feedparser", "feedparser.*"]
ignore_missing_imports = true
```

This suppresses missing import errors for feedparser. While feedparser doesn't have type stubs, this means any import error in feedparser-related code is silently ignored.

**Fix:** Low priority — consider creating a minimal type stub file for the feedparser interface used.

### [L6] `parse_provider_budgets` uses raw dict indexing without KeyError safety

**File:** `src/sift/services/search_service.py:49-55`

```python
parsed[provider] = SearchProviderBudget(
    max_requests_per_run=int(raw_value["max_requests_per_run"]),
    ...
)
```

If a budget config is missing a key, this raises an unhandled `KeyError`. The config validation in `registry.py` should catch this, but the service method itself is not defensive.

**Fix:** Use `.get()` with defaults or validate keys before accessing.

---

## Test Gaps

### Backend (79% coverage)

| Area | Coverage | Gap |
|------|----------|-----|
| `worker.py` | 0% | No tests at all |
| `scheduler.py` | 40% | Loop and metrics untested |
| `ingestion_service.py` | 57% | Core ingest path partially tested |
| `streams.py` (API) | 44% | Many endpoints untested |
| `rules.py` (API) | 44% | Many endpoints untested |
| `folders.py` (API) | 49% | CRUD partially tested |
| `search_provider_noop.py` | 0% | No tests |
| `keyword_heuristic_classifier.py` | 29% | Classifier logic untested |
| `discovery_service.py` | 67% | Generation/persistence partially tested |
| `filter_service.py` | 61% | Preview logic untested |
| `stream_service.py` | 78% | Classifier runs and backfill paths partially covered |

### Frontend

- 3 pre-existing test failures in `MonitoringFeedsPage.test.tsx`
- No E2E tests (Playwright is installed but no test files found)
- No error boundary tests
- No auth route guard tests

### Security test gaps

- No tests for SSRF protection on fulltext fetch (the validation exists but is it tested for all edge cases?)
- No tests for SSRF on feed ingestion (because there is no protection — see C1)
- No tests for cookie security attributes in production vs development
- No tests for CORS behavior

---

## Summary — Top 5 Fixes (Priority Order)

1. **[C1+C2] Add SSRF validation to ingestion and discovery services** — Extract SSRF validation from fulltext service into shared utility, apply to feed ingestion (C1), discovery candidate validation (C2), and search provider runtime. Include redirect-target validation.

2. **[C3] Replace xml.etree.ElementTree with defusedxml in OPML parser** — Prevent XXE/entity expansion attacks on user-uploaded OPML files.

3. **[H3+H5+H6] Fix memory exhaustion vectors** — Cap advanced search scan (H3), add OPML file size limit + recursion depth limit (H5), add ingestion response size limit (H6).

4. **[M1+M2] Fix CI format/lint failures** — Run `ruff format` on backend and `eslint --fix` on frontend to restore green CI.

5. **[H1] Secure cookie default + [M12] Redact redis_url in logs** — Make `auth_cookie_secure` default to `True` in production, redact credentials from startup logs.

---

## Architecture Notes

**Strengths:**
- Clean modular monolith with explicit service boundaries
- Plugin system with timeout/fault isolation and telemetry
- DOMPurify sanitization on frontend is properly implemented
- SSRF protection on fulltext fetch is thorough (DNS resolution check, private IP check)
- Alembic migrations are comprehensive (19 migrations matching models)
- Observability is well-integrated (structured logging, Prometheus metrics, request correlation)
- Frontend sanitization chain is sound: raw → `toReaderHtml()` → DOMPurify → highlight → render

**Areas for improvement:**
- User ID type inconsistency (str vs UUID) is a latent data model issue
- No rate limiting on auth endpoints
- Frontend bundle needs code-splitting
- Several API route files have low test coverage (streams, rules, folders)
- Worker and scheduler processes have minimal test coverage