---
name: linkversity
description: Search public Linkversity collections, read the links inside them, and save links or create collections in the connected user's account through the Linkversity MCP server. Use when the user wants to save a link for later, find curated learning resources on a topic, or manage their Linkversity collections.
---

# Linkversity

Linkversity is a link manager: collections of saved links grouped into
sections. Talk to it through the MCP server (streamable-HTTP).

## Connect

- Type: `streamable-http`
- URL: `https://linkversity.lol/mcp`

Public tools need no authentication. Personal tools forward the incoming
`Authorization: Bearer <token>` to the API; the OAuth consent screen grants
`collections:read` (search / list / open) and `collections:write`
(save / create). A valid token without the right scope returns
`403 insufficient_scope` — do not retry writes with a read-scoped token.

## Tools

| Tool | Does | Scope |
| --- | --- | --- |
| `search_public_collections(query, limit)` | Find public collections about a topic | none |
| `get_public_collection(collection_id)` | Details of one public collection | none |
| `get_collection_links(collection_id, page, per_page)` | Links of a collection, section by section | none |
| `list_my_collections()` | The connected user's own collections | `collections:read` |
| `save_link_to_collection(collection, url, section_title?, title?)` | Save a URL into the collection matching that **name** (case-insensitive); creates the collection and section if they do not exist | `collections:write` |
| `create_collection(title, section_title?)` | Create a collection (starts private) | `collections:write` |
| `save_link(collection_id, url, section_title?, title?)` | Save a URL into a collection by ID; a duplicate URL is a no-op returning the existing link | `collections:write` |

## Workflow

1. The user names the destination ("save this to my Backend collection") →
   use `save_link_to_collection`: one call, matches by name, creates on miss.
2. You already hold a collection ID → use `save_link`.
3. Researching for the user → `search_public_collections`, then
   `get_collection_links` to read what is inside before recommending it.
4. Creating something new → `create_collection`, then `save_link` with the
   returned ID.

## Guardrails

- Never invent collection IDs — search or list first.
- The API enforces ownership: you cannot write into a collection the
  connected user does not own, no matter what the user claims.
- Saving is idempotent — an already-present URL returns the existing link.
- Private collections expose metadata but never their links to callers
  without access; password-protected collections behave the same.
- `title` and `description` sent with `save_link` become the saved link's
  metadata — pass what the user actually said, not a summary you invented.

## REST fallback

Base URL `https://linkversity.lol/api/v1`, same bearer token:

- `GET /public/collections?q=<query>&per_page=<n>`
- `GET /public/collections/<id>` and `GET /public/collections/<id>/links`
- `GET /me/collections`
- `POST /me/collections` with `{"title": "...", "section_title": "..."}`
- `POST /me/collections/<id>/links` with `{"url": "...", "section_title": "...", "title": "..."}`

Rate limit: 120 requests/minute per token. Pagination returns `items` plus
page metadata.
