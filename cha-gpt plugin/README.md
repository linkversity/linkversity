# Linkversity ChatGPT plugin

Zip this folder and upload it in ChatGPT → Plugins → **Upload new or existing
plugin**. The plugin connects to the Linkversity MCP server and lets ChatGPT:

- search public Linkversity collections by topic
- read the links inside a collection (with source URLs)
- list your own collections after you connect your account
- turn a collection into a personalized study plan

## Contents

| File | Purpose |
| --- | --- |
| `plugin.json` | Portable plugin manifest (name, version, interface metadata) |
| `mcp.json` | MCP server declaration (`streamable-http`) |
| `assets/logo.png` | Plugin logo |
| `assets/icon.png` | Composer icon |

## Before you upload

1. Make sure the MCP server is running and reachable over **HTTPS** at the URL
   in `mcp.json` (`https://linkversity.lol/mcp`). See `../mcp-server/README.md`
   for the nginx proxy snippet.
2. If your domain differs, edit `mcp.json` (`mcpServers.linkversity.url`) and
   the URLs in `plugin.json`.
3. Verify the domain in the OpenAI developer dashboard (required for the
   hosted connection).

## Zip it

```bash
cd "cha-gpt plugin"
zip -r linkversity-plugin.zip plugin.json mcp.json assets
```

Upload `linkversity-plugin.zip`. In the plugin's MCP configuration step,
ChatGPT scans `mcp.json` and connects to the server. One MCP server per plugin.

## Auth

OAuth 2.0 (authorization code + PKCE S256) is implemented in the Flask app
(`modules/box__linkolearn/apiv1/oauth.py`):

| Endpoint | Purpose |
| --- | --- |
| `/.well-known/oauth-authorization-server` | discovery metadata |
| `/.well-known/oauth-protected-resource` | resource metadata |
| `POST /oauth/register` | dynamic client registration (RFC 7591) |
| `GET /oauth/authorize` | consent screen (user logs in, approves) |
| `POST /oauth/token` | code / refresh-token exchange |
| `GET /oauth/userinfo` | identity for a bearer token |

Flow: ChatGPT hits `/oauth/register`, sends the user to `/oauth/authorize`,
exchanges the code (with PKCE verifier) at `/oauth/token`, then forwards the
resulting `Authorization: Bearer` header on every MCP call. The MCP server
passes it straight through to the Flask API, which validates the token and
enforces the `collections:read` scope.

Apply the DB migration first (adds the `oauth_*` tables):

```bash
FLASK_APP=app.py flask db upgrade
```

Notes:

- `mcp.json` declares the OAuth endpoints; replace the domain if yours differs.
- Tokens are stored hashed (SHA-256); access tokens expire in 7 days, refresh
  tokens in 90 days; authorization codes are single-use and expire in 5 min.
- API-key auth is not supported by the submission portal's connection form;
  OAuth is the supported path.
