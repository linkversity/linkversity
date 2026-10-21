# Linkversity ChatGPT plugin

Zip this folder and upload it in ChatGPT → Plugins → **Upload new or existing
plugin**. The plugin connects to the Linkversity MCP server and lets ChatGPT:

- search public Linkversity collections by topic
- read the links inside a collection (with source URLs)
- list your own collections after you connect your account
- save links and create collections from the chat

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

Auth is declared in `mcp.json` under the server's
`extensions["com.openai"].auth` (field names are case-sensitive camelCase):

- `type: "mixed"` - the public tools work without signing in; the personal
  tools (`list_my_collections`, `save_link_to_collection` on your own
  collections) trigger OAuth
- `client.mode: "dcr"` - ChatGPT registers itself through our RFC 7591
  dynamic client registration (`POST /oauth/register`); no client credentials
  in the package
- endpoint URLs are **not** hardcoded - the OAuth discovery document
  (`/.well-known/oauth-authorization-server`) supplies authorize/token/
  registration endpoints, per the docs' "omit overrides when discovery
  supplies them"
- `baseScopes: ["collections:read"]` - the only scope the API issues

Flow: ChatGPT discovers OAuth from the MCP endpoint, registers a client, sends
the user to the consent screen, exchanges the code (PKCE S256) at
`/oauth/token`, then forwards the bearer token on MCP calls. The MCP server
passes it through; the Flask API validates it and enforces the scope.

Apply the DB migration first (adds the `oauth_*` tables):

```bash
FLASK_APP=app.py flask db upgrade
```

Notes:

- `mcp.json` must stay schema-clean: `type`/`url` plus the documented
  `extensions.com.openai.auth` object only - unknown or snake_case fields
  make the portal reject the whole file ("does not reference any MCP
  server" → misclassified as skills-only, which they no longer accept)
- Tokens are stored hashed (SHA-256); access tokens expire in 7 days, refresh
  tokens in 90 days; authorization codes are single-use and expire in 5 min
- API-key auth is not supported by the submission portal's connection form;
  OAuth is the supported path
