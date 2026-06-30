# Sift Development Cycle Plan — 2026-06-30

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Fix critical/high review findings, restore CI to green, and advance the next backlog priorities (monitoring feed management v2 + SearXNG verification).

**Architecture:** This plan addresses three workstreams in parallel: (1) security and CI hygiene fixes from the code review, (2) backend reliability improvements, (3) backlog advancement on the current priorities. Each workstream is independent and can be developed on separate feature branches from `develop`.

**Tech Stack:** Python 3.13 + FastAPI + SQLAlchemy async + Ruff + Mypy + Pytest (backend); React 19 + TypeScript + MUI 7 + Vite + Vitest (frontend)

**Decisions captured:**
- SSRF validation is extracted into a shared utility, not duplicated
- Advanced search gets a scan cap as an interim fix (full DB acceleration is deferred backlog #6)
- Frontend code-splitting uses route-level dynamic imports (simplest, highest impact)
- Frontend Dockerfile uses multi-stage build (node build → nginx serve)
- Cookie secure flag is env-aware (False in development, True otherwise)

**Assumptions:**
- `auth_cookie_secure` is currently `False` by default (`src/sift/config.py`, confirmed via Settings())
- The ingestion service has no URL validation (`src/sift/services/ingestion_service.py:178`)
- The fulltext service has SSRF protection (`src/sift/services/article_fulltext_service.py:167-201`)
- 19 Alembic migrations exist and match the current models
- Frontend has no Dockerfile (checked `frontend/Dockerfile` — does not exist)

---

## Workstream A: Security & CI Fixes (from code review)

### Task A1: Extract shared SSRF URL validation utility

**Objective:** Create a shared URL validation module from the existing fulltext service code.

**Files:**
- Create: `src/sift/services/url_validation.py`
- Modify: `src/sift/services/article_fulltext_service.py:1-7, 167-201` (remove duplication, import from shared)

**Step 1: Write failing test**

```python
# tests/test_url_validation.py
import pytest
from sift.services.url_validation import validate_fetch_url, UrlValidationError

def test_validate_fetch_url_rejects_localhost():
    with pytest.raises(UrlValidationError, match="Loopback"):
        validate_fetch_url("http://localhost/admin")

def test_validate_fetch_url_rejects_private_ip():
    with pytest.raises(UrlValidationError, match="Private"):
        validate_fetch_url("http://10.0.0.1/internal")

def test_validate_fetch_url_rejects_metadata_endpoint():
    with pytest.raises(UrlValidationError, match="Private"):
        validate_fetch_url("http://169.254.169.254/latest/meta-data/")

def test_validate_fetch_url_accepts_public_url():
    result = validate_fetch_url("https://example.com/feed.xml")
    assert result == "https://example.com/feed.xml"

def test_validate_fetch_url_rejects_non_http_scheme():
    with pytest.raises(UrlValidationError, match="scheme"):
        validate_fetch_url("file:///etc/passwd")
```

**Step 2: Run test to verify failure**

Run: `pytest tests/test_url_validation.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

Extract the validation logic from `article_fulltext_service.py:167-201` into `src/sift/services/url_validation.py`:

```python
import ipaddress
import socket
from typing import Final
from urllib.parse import urlparse

_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


class UrlValidationError(Exception):
    pass


def validate_fetch_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UrlValidationError("Unsupported URL scheme. Only http/https are allowed.")
    if not parsed.hostname:
        raise UrlValidationError("URL is missing a hostname.")
    _assert_public_host(parsed.hostname)
    return parsed.geturl()


def _assert_public_host(hostname: str) -> None:
    if hostname.lower() == "localhost":
        raise UrlValidationError("Loopback/localhost fetch targets are not allowed.")
    try:
        _assert_public_ip(ipaddress.ip_address(hostname))
        return
    except ValueError:
        pass
    try:
        addresses = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlValidationError(f"Failed resolving URL host: {exc}") from exc
    for entry in addresses:
        ip_raw = entry[4][0]
        _assert_public_ip(ipaddress.ip_address(ip_raw))


def _assert_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        raise UrlValidationError("Private or non-routable fetch targets are not allowed.")
```

**Step 4: Run test to verify pass**

Run: `pytest tests/test_url_validation.py -v`
Expected: PASS

**Step 5: Refactor article_fulltext_service to use shared module**

Replace the local `_validate_fetch_url`, `_assert_public_host`, `_assert_public_ip` functions in `article_fulltext_service.py` with an import from `url_validation.py`. Rename `ArticleFulltextValidationError` usage to map from `UrlValidationError` or keep a thin wrapper.

**Step 6: Run full test suite**

Run: `pytest tests/test_article_fulltext_service.py tests/test_article_fulltext_api.py tests/test_url_validation.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/sift/services/url_validation.py tests/test_url_validation.py src/sift/services/article_fulltext_service.py
git commit -m "refactor(security): extract SSRF URL validation into shared utility"
```

---

### Task A2: Apply SSRF validation to feed ingestion and discovery

**Objective:** Add SSRF validation to the ingestion service and discovery candidate validation before fetching URLs.

**Files:**
- Modify: `src/sift/services/ingestion_service.py:177-179` (add validation before httpx.get)
- Modify: `src/sift/services/discovery_service.py:978-980, 1040, 1058` (add validation before each client.get)
- Modify: `src/sift/services/feed_service.py:27-48` (validate URL at creation time)
- Test: `tests/test_ingestion_service.py`, `tests/test_feed_service.py`, `tests/test_discovery_service.py`

**Step 1: Write failing tests**

```python
# tests/test_ingestion_service.py — add test
async def test_ingest_feed_rejects_ssrf_target(...):
    # Create feed with localhost URL, attempt ingest, expect error
    ...

# tests/test_feed_service.py — add test
async def test_create_feed_rejects_private_url(...):
    # Attempt to create feed with http://10.0.0.1/feed, expect error
    ...

# tests/test_discovery_service.py — add test
async def test_discovery_validation_rejects_ssrf_candidate(...):
    # Candidate with internal URL, expect validation failure
    ...
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_ingestion_service.py::test_ingest_feed_rejects_ssrf_target -v`
Expected: FAIL — no validation

**Step 3: Implement**

In `ingestion_service.py`, before line 178:
```python
from sift.services.url_validation import validate_fetch_url, UrlValidationError

# ... in ingest_feed method, before the httpx call:
try:
    validated_url = validate_fetch_url(feed.url)
except UrlValidationError as exc:
    feed.last_fetch_error = str(exc)
    feed.last_fetch_error_at = datetime.now(UTC)
    await session.commit()
    result.errors.append(str(exc))
    _record_ingest_observability(...)
    return result
```

In `discovery_service.py`, in `_validate_candidates` and `_is_valid_feed_endpoint`, validate each URL before `client.get(url)`:
```python
from sift.services.url_validation import validate_fetch_url, UrlValidationError

# Before each client.get(url) call:
try:
    validate_fetch_url(url)
except UrlValidationError:
    # skip this URL, add warning
    continue
```

In `feed_service.py`, in `create_feed()`, validate the URL before creating the Feed:
```python
from sift.services.url_validation import validate_fetch_url, UrlValidationError

try:
    validate_fetch_url(str(data.url))
except UrlValidationError as exc:
    raise FeedValidationError(str(exc)) from exc
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_ingestion_service.py tests/test_feed_service.py tests/test_discovery_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sift/services/ingestion_service.py src/sift/services/discovery_service.py src/sift/services/feed_service.py tests/
git commit -m "fix(security): apply SSRF validation to feed ingestion, creation, and discovery candidate validation"
```

---

### Task A3: Fix backend ruff format failures

**Objective:** Restore green CI by formatting all backend files.

**Files:** 15 files listed by `ruff format --check`

**Step 1: Run formatter**

Run: `ruff format src tests`

**Step 2: Verify**

Run: `ruff format --check src tests`
Expected: "89 files already formatted" — no reformat needed

**Step 3: Run tests to verify no regressions**

Run: `pytest -q`
Expected: 146 passed

**Step 4: Commit**

```bash
git add -A
git commit -m "style: ruff format all backend files"
```

---

### Task A4: Fix frontend ESLint errors

**Objective:** Fix 6 unnecessary type assertion errors.

**Files:**
- `frontend/src/entities/article/model.ts:114, 148`
- `frontend/src/entities/navigation/model.ts:113`
- `frontend/src/entities/user/model.ts:16`
- `frontend/src/features/feed-health/routes/FeedHealthPage.tsx:248`
- `frontend/src/features/monitoring/routes/MonitoringFeedsPage.tsx:569`

**Step 1: Run eslint --fix**

Run: `cd frontend && npx eslint . --fix`

**Step 2: Verify**

Run: `cd frontend && npx eslint .`
Expected: no errors

**Step 3: Run typecheck to verify no type regressions**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "fix(frontend): remove unnecessary type assertions"
```

---

### Task A5: Make auth cookie secure flag production-aware

**Objective:** Default `auth_cookie_secure` to `True` in non-development environments.

**Files:**
- Modify: `src/sift/config.py` (add validator for auth_cookie_secure)
- Test: `tests/test_auth_api.py`

**Step 1: Write failing test**

```python
def test_auth_cookie_secure_in_production():
    # Override env to production, verify auth_cookie_secure defaults to True
    ...
```

**Step 2: Implement**

In `src/sift/config.py`, add a model validator:
```python
from pydantic import model_validator

@model_validator(mode="after")
def _enforce_secure_cookie_in_production(self) -> "Settings":
    if self.env.lower() != "development" and not self.auth_cookie_secure:
        # In production, cookies must be secure
        # Only warn if explicitly set to False — but default to True
        pass
    return self
```

Better approach: change the default to `True` and set it to `False` only in dev container env.

**Step 3: Verify and commit**

```bash
git add src/sift/config.py tests/test_auth_api.py
git commit -m "fix(security): default auth_cookie_secure to True in production"
```

---

### Task A6: Create frontend Dockerfile

**Objective:** Add a multi-stage Dockerfile for the frontend so CI can publish `sift-frontend` to GHCR.

**Files:**
- Create: `frontend/Dockerfile`

**Step 1: Write Dockerfile**

```dockerfile
# Build stage
FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Also create `frontend/nginx.conf` for SPA routing fallback.

**Step 2: Verify build**

Run: `docker build -t sift-frontend-test frontend/`
Expected: successful build

**Step 3: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "feat(deploy): add frontend Dockerfile for GHCR publish"
```

---

### Task A7: Replace xml.etree.ElementTree with defusedxml in OPML parser

**Objective:** Prevent XXE/entity expansion attacks on user-uploaded OPML files.

**Files:**
- Modify: `pyproject.toml` (add `defusedxml` dependency)
- Modify: `src/sift/services/opml_service.py:4, 32, 59, 75-79` (switch to defusedxml)
- Test: `tests/test_opml_service.py`

**Step 1: Add dependency**

Add `defusedxml>=0.7` to `pyproject.toml` dependencies, run `uv sync`.

**Step 2: Replace imports**

In `opml_service.py`:
```python
# Replace: from xml.etree import ElementTree
from defusedxml import ElementTree
```

**Step 3: Write test for entity expansion rejection**

```python
def test_opml_rejects_billion_laughs():
    payload = b'''<?xml version="1.0"?>
    <!DOCTYPE lolz [
     <!ENTITY lol "lol">
     <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;">
    ]>
    <opml><body><outline text="&lol2;"/></body></opml>'''
    with pytest.raises(OpmlParseError):
        opml_service.import_from_bytes(session=..., user_id=..., content=payload)
```

**Step 4: Verify and commit**

```bash
git add pyproject.toml src/sift/services/opml_service.py tests/test_opml_service.py
git commit -m "fix(security): use defusedxml to prevent XXE in OPML parser"
```

---

### Task A8: Add size limits to ingestion and OPML import

**Objective:** Prevent memory exhaustion from large feed responses and OPML uploads.

**Files:**
- Modify: `src/sift/services/ingestion_service.py:178` (add response size check)
- Modify: `src/sift/api/routes/imports.py:26` (add upload size check)
- Modify: `src/sift/services/opml_service.py:59` (add recursion depth limit)
- Test: `tests/test_ingestion_service.py`, `tests/test_opml_service.py`

**Step 1: Add ingestion response size limit**

In `ingestion_service.py`, after receiving the response:
```python
MAX_FEED_BYTES = 5_000_000  # 5MB

if response.status_code == 200:
    content_length = int(response.headers.get("content-length", 0))
    if content_length > MAX_FEED_BYTES:
        # abort, record error
        ...
    body = response.content
    if len(body) > MAX_FEED_BYTES:
        # abort, record error
        ...
```

**Step 2: Add OPML upload size limit**

In `imports.py`:
```python
content = await file.read()
if len(content) > 5_000_000:
    raise HTTPException(status_code=413, detail="OPML file too large (max 5MB)")
```

**Step 3: Add recursion depth limit to _extract_entries**

In `opml_service.py`:
```python
def _extract_entries(node, into, depth=0, max_depth=100):
    if depth > max_depth:
        return
    ...
    _extract_entries(child, into, depth=depth+1, max_depth=max_depth)
```

**Step 4: Verify and commit**

```bash
git add src/sift/services/ingestion_service.py src/sift/api/routes/imports.py src/sift/services/opml_service.py tests/
git commit -m "fix(security): add response size limits and OPML recursion depth limit"
```

---

### Task A9: Redact redis_url in scheduler/worker logs

**Objective:** Prevent credential leakage in startup logs.

**Files:**
- Modify: `src/sift/tasks/scheduler.py:210`
- Modify: `src/sift/tasks/worker.py:33`
- Test: `tests/test_scheduler.py`

**Step 1: Add redaction helper**

```python
from urllib.parse import urlparse, urlunparse

def _redact_redis_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.password:
        netloc = parsed.netloc.replace(parsed.password, "***")
        return urlunparse(parsed._replace(netloc=netloc))
    return url
```

**Step 2: Replace `settings.redis_url` with `_redact_redis_url(settings.redis_url)` in log extra dicts**

**Step 3: Verify and commit**

```bash
git add src/sift/tasks/scheduler.py src/sift/tasks/worker.py
git commit -m "fix(security): redact redis credentials from scheduler/worker startup logs"
```

---

### Task A10: Fix rule_service.to_out action bug

**Objective:** Fix the hardcoded `action="drop"` in rule serialization.

**Files:**
- Modify: `src/sift/services/rule_service.py:239`
- Test: `tests/test_rule_service.py`

**Step 1: Fix the bug**

Change line 239 from `action="drop"` to `action=rule.action`.

**Step 2: Add test**

```python
def test_to_out_uses_rule_action():
    rule = IngestRule(action="drop")
    out = rule_service.to_out(rule)
    assert out.action == "drop"
    # If future actions are added, verify they pass through
```

**Step 3: Verify and commit**

```bash
git add src/sift/services/rule_service.py tests/test_rule_service.py
git commit -m "fix(rules): use rule.action in to_out instead of hardcoded 'drop'"
```

---

## Workstream B: Backend Reliability

### Task B1: Add scan cap to advanced search

**Objective:** Prevent the advanced search from loading all articles into memory.

**Files:**
- Modify: `src/sift/services/article_service.py:213-226` (add LIMIT to advanced search scan)
- Test: `tests/test_search_service.py`

**Step 1: Write failing test**

```python
async def test_advanced_search_caps_scan_results(...):
    # Insert 200 articles, run advanced search, verify not all loaded
    ...
```

**Step 2: Implement**

In `article_service.py:213`, add a scan limit:
```python
ADVANCED_SEARCH_SCAN_LIMIT = 10000

# ... in list_articles advanced path:
all_rows_result = await session.execute(
    base_query.where(*filters)
    .order_by(*_sorting_clause(sort=sort, read_expr=context.read_expr))
    .limit(ADVANCED_SEARCH_SCAN_LIMIT)
)
```

If the result count equals the limit, set a `truncated` flag in the response.

**Step 3: Verify and commit**

```bash
git add src/sift/services/article_service.py tests/test_search_service.py
git commit -m "fix(performance): cap advanced search scan to prevent memory exhaustion"
```

---

### Task B2: Batch mark_scope_as_read for large result sets

**Objective:** Prevent large `IN (...)` queries in mark_scope_as_read.

**Files:**
- Modify: `src/sift/services/article_service.py:454-461` (batch the IDs)
- Test: `tests/test_article_service.py`

**Step 1: Implement batching**

In `mark_scope_as_read`, after collecting `article_ids`, batch the update:
```python
BATCH_SIZE = 500
total_updated = 0
for i in range(0, len(article_ids), BATCH_SIZE):
    batch = article_ids[i : i + BATCH_SIZE]
    total_updated += await self.bulk_patch_state(
        session=session, user_id=user_id, article_ids=batch,
        is_read=True, is_starred=None, is_archived=None,
    )
return total_updated
```

**Step 2: Verify and commit**

```bash
git add src/sift/services/article_service.py tests/test_article_service.py
git commit -m "fix(performance): batch mark_scope_as_read to avoid large IN queries"
```

---

## Workstream C: Backlog Advancement

### Task C1: SearXNG instance compatibility verification

**Objective:** Validate SearXNG instance compatibility with the runtime adapter contract, test candidate public instances, and document test configuration guidance.

**Files:**
- Modify: `src/sift/plugins/builtin/search_provider_runtime.py` (if adapter fixes needed)
- Create: `docs/specs/done/searxng-verification-2026-06-30.md` (verification report)
- Modify: `config/plugins.yaml` (update test config guidance)

**Step 1: Review adapter contract**

Read `src/sift/plugins/builtin/search_provider_runtime.py` and verify the SearXNG adapter uses `/search` + `format=json` as documented in the backlog.

**Step 2: Test against candidate instances**

Test 3-5 public SearXNG instances for:
- Auth requirements
- Rate limits
- API compatibility (`format=json` support)
- Response time

**Step 3: Document findings**

Write a verification report with:
- Compatible instances shortlist
- Recommended test endpoint
- Config guidance for local/session testing

**Step 4: Commit**

```bash
git add docs/specs/done/searxng-verification-2026-06-30.md config/plugins.yaml
git commit -m "feat(discovery): verify SearXNG instance compatibility and document test config"
```

---

### Task C2: Monitoring feed search management v2 — expand management capabilities

**Objective:** Begin expanding monitoring definition management capabilities per backlog priority #1.

**Files:**
- Read: `docs/specs/monitoring-signal-scoring-v1.md` (parent spec)
- Read: `src/sift/api/routes/streams.py` (current monitoring API)
- Read: `src/sift/services/stream_service.py` (current service)

**Step 1: Review current capabilities**

Read the current monitoring stream API and identify gaps vs the backlog item:
- expand monitoring definition management capabilities
- add optional create/update-triggered historical matching pass
- continue explainability refinements for plugin/query evidence surfaces

**Step 2: Design the v2 expansion slice**

Define which management capabilities to add first (e.g., bulk update, reorder, import/export).

**Step 3: Implement and test**

Follow TDD for each new capability.

---

## Deferred items (from review, not in this cycle)

- [M8] User ID type standardization (str → UUID) — requires migration, defer to a dedicated data model consistency sprint
- [M9] Auth rate limiting — add when OIDC integration is planned (backlog #8)
- [L1] Service singleton → DI refactor — low priority, works correctly
- [L4] Scheduler/worker test coverage — incremental improvement, not blocking
- [H2] CORS production hardening — address in deployment config sprint
- Frontend code-splitting (M4) — defer to a frontend performance sprint
- Dashboard command center v1 — blocked by spec-gate checklist (backlog deferred #2)
- Stream ranking/prioritization — deferred backlog #1
- LLM summary plugin — deferred backlog #4
- Vector DB integration — deferred backlog #9

---

## Final Verification

After all tasks in Workstream A are complete:

1. Run `ruff check src tests && ruff format --check src tests` — expected: clean
2. Run `pytest -q` — expected: all pass
3. Run `cd frontend && npx tsc --noEmit && npx eslint .` — expected: clean
4. Run `cd frontend && npx vitest run` — expected: no new failures
5. Run `cd frontend && npx vite build` — expected: successful build
6. Verify Docker builds: `docker build -t sift-backend-test . && docker build -t sift-frontend-test frontend/`
7. Commit with `[verified]` prefix after final review pass