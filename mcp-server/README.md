# Linkversity MCP server

Standalone FastMCP process that exposes Linkversity to ChatGPT. It does **not**
import Flask - it calls the Linkversity REST API over HTTP (`/api/v1/...`),
so it can be deployed, scaled and rotated independently.

## Run

```bash
cd mcp-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export LINKVERSITY_API_URL="https://linkversity.lol"   # the Flask app
export LINKVERSITY_MCP_PORT=8001
python server.py
```

Endpoint: `http://0.0.0.0:8001/mcp` (streamable-http, stateless).

## Environment variables

All optional; defaults shown. Set them in the systemd unit (see
`Environment=` lines in `~/code/notes/linkversity/linkversity-mcp.service`)
or export them when running by hand.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LINKVERSITY_API_URL` | `http://127.0.0.1:5000` | Base URL of the Flask app the tools call. Production: `https://linkversity.lol` |
| `LINKVERSITY_MCP_HOST` | `0.0.0.0` | Bind address. Use `127.0.0.1` in production - nginx is the only intended client |
| `LINKVERSITY_MCP_PORT` | `8001` | Listen port (must match the nginx `proxy_pass`) |
| `LINKVERSITY_API_TIMEOUT` | `15` | Seconds before a Flask API call is aborted |
| `LINKVERSITY_MCP_ALLOWED_HOST` | `linkversity.lol` | Public hostname accepted in the `Host` header (DNS-rebinding protection). Extra hosts can't be added here - edit `allowed_hosts` in `server.py` for more |
| `LINKVERSITY_API_TOKEN` | *(unset)* | **Dev only.** Fallback bearer token forwarded to the API when the incoming MCP request has no `Authorization` header. Leave unset in production - it would apply to every unauthenticated caller |

Minimum for production:

```ini
Environment="LINKVERSITY_API_URL=https://linkversity.lol"
Environment="LINKVERSITY_MCP_HOST=127.0.0.1"
Environment="LINKVERSITY_MCP_ALLOWED_HOST=linkversity.lol"
```

## Auth

- **Public tools** (`search_public_collections`, `get_public_collection`,
  `get_collection_links` on a public collection) need no auth.
- **Personal tools** (`list_my_collections` on your own
  collections): if the incoming MCP request carries `Authorization: Bearer
  <token>`, it is forwarded to the Flask API. OAuth access tokens issued by
  the app (`/oauth/*`) work out of the box - the API resolves them directly.
- For local testing without OAuth you can set `LINKVERSITY_API_TOKEN` to one of
  your account's API tokens; it is used only when no header is present.

## Reverse proxy (TLS)

ChatGPT requires HTTPS. In production, proxy `/mcp` on the main domain to
this process. Example nginx:

```nginx
location /mcp {
    proxy_pass http://127.0.0.1:8001/mcp;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # streamable-http / SSE - buffering MUST be off or responses stall
    proxy_buffering off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

Full ready-to-paste files:
`~/code/notes/linkversity/linkversity-mcp.nginx` and
`~/code/notes/linkversity/linkversity-mcp.service`.

Then the public MCP URL is `https://linkversity.lol/mcp` and matches
`cha-gpt plugin/mcp.json`.

## Tools

| Tool | API | Auth |
| --- | --- | --- |
| `search_public_collections` | `GET /api/v1/public/collections` | none |
| `get_public_collection` | `GET /api/v1/public/collections/{id}` | none |
| `list_my_collections` | `GET /api/v1/me/collections` | user (read) |
| `get_collection_links` | `GET /api/v1/{public,me}/collections/{id}/links` | optional |
| `create_collection` | `POST /api/v1/me/collections` | user (write) |
| `save_link` | `POST /api/v1/me/collections/{id}/links` | user (write) |
| `save_link_to_collection` | `GET /api/v1/me/collections` + `POST ...` (match by name, create on miss) | user (write) |

Read tools require the `collections:read` scope; write tools require
`collections:write` (both are in `baseScopes` and shown on the consent
screen). Missing scope returns `403 insufficient_scope`.

## Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# transport: streamable-http, URL: http://127.0.0.1:8001/mcp
```
