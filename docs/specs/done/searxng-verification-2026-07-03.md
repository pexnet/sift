# SearXNG Instance Compatibility Verification

**Date:** 2026-07-03
**Status:** Completed

## Objective

Validate SearXNG instance compatibility with the Sift runtime adapter contract, test candidate public instances for API/JSON access, and document test configuration guidance.

## Adapter Contract

The Sift SearXNG adapter (`src/sift/plugins/builtin/search_provider_runtime.py:_search_searxng`) uses:

- **Endpoint:** `{base_url}` (configurable via `provider_settings.base_url`, defaults to `http://localhost:8080/search`)
- **HTTP method:** GET
- **Query params:** `q={query}`, `format=json`, `language=en-US`, `safesearch=0`
- **Headers:** `User-Agent: sift-search-provider/1.0`
- **Timeout:** 4 seconds (`_DEFAULT_TIMEOUT_SECONDS`)
- **Response shape:** JSON object with `results` array; each result has `url`, `title`, `content` (optional), `parsed_url` (optional)

The adapter correctly handles:
- HTTP 429 → `http_status_429` warning code
- HTTP 4xx → `http_status_4xx` warning code
- HTTP 5xx → `http_status_5xx` warning code
- Timeout → `timeout` warning code
- Network errors → `network_error` warning code
- Invalid JSON → `invalid_json` warning code
- Missing/invalid `results` list → `invalid_response_payload` warning code

## Public Instance Testing

Tested 17+ public SearXNG instances (from searx.space and known lists) against the adapter contract.

### Results Summary

| Instance | HTTP Status | JSON API | Notes |
|----------|-------------|----------|-------|
| `searx.be` | 403 | ❌ | Forbidden (openresty WAF) |
| `searx.tiekoetter.com` | 429 | ❌ | Rate limited |
| `searx.work` | 200 (HTML) | ❌ | Returns HTML, not JSON; JS fingerprint redirect |
| `searxng.site` | 403 | ❌ | Forbidden (Apache WAF) |
| `search.sapti.me` | 429 | ❌ | Rate limited |
| `search.ononoki.org` | 429 | ❌ | Rate limited |
| `search.inetol.net` | 429 | ❌ | Rate limited |
| `searx.tuxcloud.net` | 429 | ❌ | Rate limited |
| `priv.au` | 429 | ❌ | Rate limited |
| `search.rhscz.eu` | 429 | ❌ | Rate limited |
| `searx.rhscz.eu` | 429 | ❌ | Rate limited |
| `searx.oloke.xyz` | 202 (HTML) | ❌ | Returns HTML challenge page |
| `searxng.website` | 403 | ❌ | Forbidden |
| `searx.linxx.net` | 429 | ❌ | Rate limited |
| `search.bladerunn.in` | 429 | ❌ | Rate limited |

Also tested with a browser-like User-Agent — same results (429/403).

### Conclusion

**No tested public SearXNG instance reliably serves JSON API responses to automated clients.** All instances either:
1. Return HTTP 429 (rate limit) — most common
2. Return HTTP 403 (WAF/bot protection)
3. Return HTML instead of JSON (JS challenge / fingerprint required)

This is expected behavior: public SearXNG instances explicitly discourage automated API usage and rate-limit JSON format requests aggressively. The `format=json` API is intended for self-hosted instances, not public ones.

## Recommendation

**Self-host SearXNG for Sift development and production.** This is the only reliable approach.

### Self-Hosted Setup (Docker)

```bash
# Run SearXNG locally via Docker
docker run -d --name searxng -p 8080:8080 \
  -e SEARXNG_BASE_URL=http://localhost:8080 \
  searxng/searxng:latest
```

For Sift dev container, add to `docker-compose.yml`:

```yaml
searxng:
  image: searxng/searxng:latest
  ports:
    - "8080:8080"
  environment:
    - SEARXNG_BASE_URL=http://localhost:8080
```

Then update `config/plugins.yaml`:

```yaml
providers:
  searxng:
    base_url: http://localhost:8080/search
```

### Self-Hosted JSON API Enablement

Self-hosted SearXNG may need `format=json` enabled in `settings.yml`:

```yaml
# In SearXNG's settings.yml
search:
  formats:
    - html
    - json
```

If JSON is not enabled, the adapter will receive HTML instead of JSON and emit `invalid_json` warning.

## Adapter Contract Verification

The adapter code is correct and matches the SearXNG API contract:
- GET request with `format=json` query parameter ✓
- Correct response shape parsing (dict with `results` list) ✓
- Proper error handling for all HTTP status codes ✓
- Timeout and network error handling ✓
- URL normalization and deduplication ✓

No adapter code changes are needed. The only gap is operational: a self-hosted SearXNG instance is required for functional testing.

## Local Instance Verification

A local SearXNG container was started and the adapter was tested end-to-end:

```bash
docker run -d --name searxng-dev -p 8080:8080 searxng/searxng:latest
# Enable JSON format in /etc/searxng/settings.yml:
#   search:
#     formats:
#       - html
#       - json
docker restart searxng-dev
```

The Sift adapter successfully returned 5 candidates for "python rss feed" with zero warnings.

**Docker networking note:** From inside the Sift dev container, use the Docker bridge IP (`172.17.0.1:8080`) or add SearXNG to the same Docker Compose network. `host.docker.internal` is not available by default on Linux.

## Test Configuration Guidance

For local development and testing:

1. **Self-host SearXNG** via Docker (see above)
2. **Enable JSON format** in SearXNG `settings.yml`
3. **Set `base_url`** in `config/plugins.yaml` to point to the local instance
4. **Budget settings** in `config/plugins.yaml` can remain as-is (they protect against excessive calls, which is irrelevant for self-hosted)
5. **Do not rely on public instances** for any automated testing — they rate-limit JSON API requests

For production deployment on VPS:
- Run SearXNG as a companion container alongside Sift
- Point `base_url` to the internal Docker network address (e.g., `http://searxng:8080/search`)
- No external SearXNG instance needed