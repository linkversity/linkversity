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

## Auth

- **Public tools** (`search_public_collections`, `get_public_collection`,
  `get_collection_links` on a public collection) need no auth.
- **Personal tools** (`list_my_collections`, `create_study_plan` on your own
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
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300s;
}
```

Then the public MCP URL is `https://linkversity.lol/mcp` and matches
`cha-gpt plugin/mcp.json`.

## Tools

| Tool | API | Auth |
| --- | --- | --- |
| `search_public_collections` | `GET /api/v1/public/collections` | none |
| `get_public_collection` | `GET /api/v1/public/collections/{id}` | none |
| `list_my_collections` | `GET /api/v1/me/collections` | user |
| `get_collection_links` | `GET /api/v1/{public,me}/collections/{id}/links` | optional |
| `create_study_plan` | `POST /api/v1/me/collections/{id}/study-plan` | user |

## Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# transport: streamable-http, URL: http://127.0.0.1:8001/mcp
```
