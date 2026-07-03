# Sift MCP Integration

Sift exposes an MCP (Model Context Protocol) server with two transport modes:

## Local (stdio) — for Hermes on the same machine

### 1. Create an API token

```bash
# Login and create token
curl -c /tmp/sift-cookies -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@user","password":"devpassword123!"}'

curl -b /tmp/sift-cookies -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"name":"Hermes MCP","scopes":["mcp:read","mcp:write"]}'
# Save the raw_token from the response
```

### 2. Configure Hermes

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  sift:
    command: "sift-mcp"
    env:
      SIFT_MCP_TOKEN: "sft_<token from step 1>"
      SIFT_DATABASE_URL: "postgresql+asyncpg://sift:sift@localhost:5432/sift"
```

### 3. Restart Hermes

```bash
hermes gateway restart  # or restart CLI
```

Tools will appear as `mcp_sift_sift_list_feeds`, `mcp_sift_sift_search_articles`, etc.

## Remote (HTTP) — for VPS deployment

### 1. Deploy Sift with TLS

Ensure the FastAPI app is behind a TLS-terminating reverse proxy (Traefik/Caddy):
- `https://sift.example.com/mcp` → FastAPI app port 8000

### 2. Create an API token (same as local)

### 3. Configure Hermes

```yaml
mcp_servers:
  sift:
    url: "https://sift.example.com/mcp"
    headers:
      Authorization: "Bearer sft_<token>"
    timeout: 60
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `sift_list_feeds` | List subscribed feeds |
| `sift_search_articles` | Search/filter articles by scope, state, query |
| `sift_get_article` | Get full article detail by ID |
| `sift_list_folders` | List feed folders (catalogs) |
| `sift_get_navigation` | Full navigation tree with unread counts |
| `sift_get_feed_health` | Feed health: stale, errors, throughput |
| `sift_list_streams` | List keyword monitoring streams |
| `sift_add_feed` | Subscribe to a new RSS feed |
| `sift_mark_articles_read` | Bulk mark articles as read |