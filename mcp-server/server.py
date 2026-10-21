"""Linkversity MCP server (standalone process).

Runs separately from Flask and calls the Linkversity REST API over HTTP:

    export LINKVERSITY_API_URL="https://linkversity.lol"
    python server.py          # streamable-http on 0.0.0.0:8001/mcp

If the incoming MCP request carries an Authorization: Bearer header, it is
forwarded to the Flask API so personal tools see the connected user.
"""

import hashlib
import json
import os
import time

import requests
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

# Explicit annotation objects (ChatGPT submission requires explicit boolean
# readOnly/destructive/openWorld hints on every tool). All Linkversity tools
# only read a bounded catalog - they never write or reach the open web.
_READONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
)

# Additive writes (create collection, save link): not read-only, but nothing
# is overwritten or destroyed, so destructive stays false. Bounded private
# workspace => openWorld false.
_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
)

# DNS-rebinding protection: only accept requests for the public host
# (nginx proxies /mcp with Host: linkversity.lol) and localhost for probes.
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        h
        for h in (
            os.environ.get("LINKVERSITY_MCP_ALLOWED_HOST", "linkversity.lol"),
            "www.linkversity.lol",
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
        )
        if h
    ],
    # Browsers (and OpenAI's server-side plugin scanner) send an Origin
    # header on cross-origin POSTs; any origin not listed gets a 403 and
    # the portal scan fails with "could not connect".
    allowed_origins=[
        "https://chatgpt.com",
        "https://www.chatgpt.com",
        "https://chat.openai.com",
        "https://platform.openai.com",
    ],
)

mcp = FastMCP(
    "Linkversity",
    instructions=(
        "Linkversity is a link manager: collections of saved links, grouped "
        "into sections. Use search_public_collections to find public "
        "collections by topic and get_public_collection / "
        "get_collection_links to read their contents. With a connected "
        "account, list_my_collections lists the user's collections, "
        "save_link_to_collection saves a URL by collection name (creating "
        "the collection or section if it does not exist yet), and "
        "save_link / create_collection are the lower-level building "
        "blocks. Every resource includes the Linkversity source URL - cite "
        "it."
    ),
    host=os.environ.get("LINKVERSITY_MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("LINKVERSITY_MCP_PORT", "8001")),
    transport_security=_security,
    stateless_http=True,
)

API_BASE_URL = os.environ.get("LINKVERSITY_API_URL", "http://127.0.0.1:5000").rstrip(
    "/"
)
TIMEOUT = int(os.environ.get("LINKVERSITY_API_TIMEOUT", "15"))


def _bearer(ctx: Context | None) -> str | None:
    """Bearer token from the incoming MCP request, else the env fallback."""
    if ctx is not None:
        try:
            auth = ctx.request_context.request.headers.get("authorization", "")
            if auth.lower().startswith("bearer ") and auth[7:].strip():
                return auth[7:].strip()
        except Exception:
            pass
    return os.environ.get("LINKVERSITY_API_TOKEN") or None


def _headers(ctx: Context | None) -> dict:
    h = {"Accept": "application/json"}
    token = _bearer(ctx)
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str, params: dict | None = None, ctx: Context | None = None):
    r = requests.get(
        f"{API_BASE_URL}{path}",
        params=params or {},
        headers=_headers(ctx),
        timeout=TIMEOUT,
    )
    return _wrap(r)


def _post(path: str, payload: dict, ctx: Context | None = None):
    r = requests.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        headers=_headers(ctx),
        timeout=TIMEOUT,
    )
    return _wrap(r)


def _wrap(r: requests.Response):
    """Return the JSON body, or a clear error dict instead of raising."""
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:500]}
    if r.status_code >= 400:
        err = body.get("error") if isinstance(body, dict) else None
        return {"error": err or f"API returned HTTP {r.status_code}"}
    return body


@mcp.tool(annotations=_READONLY)
def search_public_collections(query: str, limit: int = 10) -> dict:
    """Find public Linkversity collections about a topic.

    Returns stable IDs, titles, descriptions and canonical URLs so you can
    open one with get_public_collection or read its links.
    """
    limit = max(1, min(limit, 50))
    return _get(
        "/api/v1/public/collections", {"q": query, "per_page": limit}
    )


@mcp.tool(annotations=_READONLY)
def get_public_collection(collection_id: int) -> dict:
    """Get the details of one public Linkversity collection by its ID."""
    return _get(f"/api/v1/public/collections/{collection_id}")


@mcp.tool(annotations=_READONLY)
def list_my_collections(ctx: Context | None = None) -> dict:
    """List the connected user's own Linkversity collections.

    Requires the user to have connected their account (an Authorization
    bearer token is forwarded to the Linkversity API).
    """
    return _get("/api/v1/me/collections", {"per_page": 50}, ctx)


@mcp.tool(annotations=_READONLY)
def get_collection_links(
    collection_id: int, page: int = 1, per_page: int = 20, ctx: Context | None = None
) -> dict:
    """List the links inside a Linkversity collection, section by section.

    Works for a public collection, or for the connected user's own collection
    when their account is connected. Returns each link's title, description,
    image and the source URL on Linkversity.
    """
    # try the connected-account view first, fall back to public
    if _bearer(ctx):
        result = _get(
            f"/api/v1/me/collections/{collection_id}/links",
            {"page": page, "per_page": per_page},
            ctx,
        )
        if "error" not in result:
            return result
    return _get(
        f"/api/v1/public/collections/{collection_id}/links",
        {"page": page, "per_page": per_page},
        ctx,
    )


@mcp.tool(annotations=_WRITE)
def save_link_to_collection(
    collection: str,
    url: str,
    section_title: str = "",
    title: str = "",
    ctx: Context | None = None,
) -> dict:
    """Save a URL into the connected user's collection *by name* (one call).

    Matches the user's collection by title, case-insensitive. If no
    collection matches, one is created (private, its first section is
    section_title). A missing section is created too. Use this when the
    user names a collection (e.g. "save this to my Backend collection");
    use save_link only when the user already gave you a collection ID.
    """
    name = (collection or "").strip()
    if not name or len(name) > 200:
        return {"error": "collection name is required (max 200 chars)"}
    listing = _get("/api/v1/me/collections", {"per_page": 100}, ctx)
    if isinstance(listing, dict) and "error" in listing:
        return listing  # not connected / bad token - surface as-is
    items = listing.get("items", []) if isinstance(listing, dict) else []
    match = next(
        (c for c in items if (c.get("title") or "").casefold() == name.casefold()),
        None,
    )
    created_collection = False
    if match is None:
        payload = {"title": name}
        if section_title:
            payload["section_title"] = section_title
        match = _post("/api/v1/me/collections", payload, ctx)
        if not isinstance(match, dict) or "error" in match or "id" not in match:
            return match if isinstance(match, dict) else {"error": "could not create collection"}
        created_collection = True
    link_payload = {"url": url}
    if section_title:
        link_payload["section_title"] = section_title
    if title:
        link_payload["title"] = title
    saved = _post(f"/api/v1/me/collections/{match['id']}/links", link_payload, ctx)
    if isinstance(saved, dict):
        saved.setdefault("collection", {"id": match["id"], "title": match.get("title")})
        if created_collection:
            saved["note"] = (saved.get("note", "") + "; collection was created").strip("; ")
    return saved


@mcp.tool(annotations=_WRITE)
def create_collection(title: str, section_title: str = "", ctx: Context | None = None) -> dict:
    """Create a new collection in the connected user's Linkversity account.

    Requires a connected account. The collection starts private; the user can
    make it public on the Linkversity website. Returns the new collection's
    ID, title and canonical URL - save links to it with save_link.
    """
    payload = {"title": title}
    if section_title:
        payload["section_title"] = section_title
    return _post("/api/v1/me/collections", payload, ctx)


@mcp.tool(annotations=_WRITE)
def save_link(
    collection_id: int,
    url: str,
    section_title: str = "",
    title: str = "",
    ctx: Context | None = None,
) -> dict:
    """Save a URL into one of the connected user's Linkversity collections.

    Requires a connected account with collections:write permission. The
    section is created if it does not exist yet; without a section_title the
    link goes into the collection's first section. Saving a URL that is
    already in the collection is a no-op and returns the existing link.
    Pass title/description to pre-fill the saved link's metadata.
    """
    payload = {"url": url}
    if section_title:
        payload["section_title"] = section_title
    if title:
        payload["title"] = title
    return _post(f"/api/v1/me/collections/{collection_id}/links", payload, ctx)


# --------------------------------------------------------------------------
# auth gate: HTTP 401 + Bearer challenge for personal tool calls
# --------------------------------------------------------------------------
#
# MCP clients only start their OAuth flow when a request comes back as
# HTTP 401 with a `WWW-Authenticate: Bearer ...` challenge. Answering 200
# with an "invalid or missing access token" JSON-RPC payload (what this
# server used to do) leaves the client believing the account is connected:
# the TUI shows "connected" while every personal tool silently fails.

_PERSONAL_TOOLS = {
    "list_my_collections",
    "save_link_to_collection",
    "create_collection",
    "save_link",
}

# token -> (valid, monotonic deadline); userinfo round-trip is skipped
# while a verdict is fresh (tools/call traffic is otherwise one extra hop
# per personal call)
_token_cache: dict[str, tuple[bool, float]] = {}
_TOKEN_CACHE_TTL = 60.0


def _token_is_valid(token: str) -> bool:
    """Ask the API whether the bearer token resolves (cached60s).

    If the API is unreachable, assume valid: the tool call should surface
    the connectivity error instead of a misleading auth challenge.
    """
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.monotonic()
    hit = _token_cache.get(key)
    if hit is not None and hit[1] > now:
        return hit[0]
    try:
        r = requests.get(
            f"{API_BASE_URL}/oauth/userinfo",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return True
    ok = r.status_code == 200
    _token_cache[key] = (ok, now + _TOKEN_CACHE_TTL)
    return ok


def _bearer_from_scope(scope) -> str:
    for name, value in scope.get("headers", []):
        if name.lower() == b"authorization":
            auth = value.decode("latin-1")
            if auth.lower().startswith("bearer "):
                return auth[7:].strip()
    return ""


class _AuthGate:
    """ASGI middleware answering personal tool calls with401 when unauthed."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        # buffer the body (the downstream app reads it after us) and decide
        pending = []
        body = b""
        while True:
            msg = await receive()
            pending.append(msg)
            if msg["type"] == "http.request":
                body += msg.get("body", b"") or b""
            if not msg.get("more_body"):
                break

        request_id = None
        needs_auth = False
        try:
            payload = json.loads(body or b"{}")
            request_id = payload.get("id")
            if payload.get("method") == "tools/call":
                name = (payload.get("params") or {}).get("name")
                needs_auth = name in _PERSONAL_TOOLS
        except ValueError:
            pass

        token = _bearer_from_scope(scope) or os.environ.get(
            "LINKVERSITY_API_TOKEN", ""
        )
        if needs_auth and (not token or not _token_is_valid(token)):
            await self._challenge(request_id, send)
            return

        async def replay():
            if pending:
                return pending.pop(0)
            while True:  # park until the client disconnects
                msg = await receive()
                if msg["type"] == "http.disconnect":
                    return msg

        await self.app(scope, replay, send)

    @staticmethod
    async def _challenge(request_id, send):
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32001,
                    "message": (
                        "authorization required: connect your Linkversity "
                        "account (OAuth). Public tools work without a token."
                    ),
                },
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (
                        b"www-authenticate",
                        (
                            'Bearer resource_metadata="'
                            f"{API_BASE_URL}/.well-known/"
                            'oauth-protected-resource"'
                        ).encode(),
                    ),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


if __name__ == "__main__":
    import uvicorn

    # uvicorn runs the Starlette app directly so the auth gate wraps the
    # streamable-http transport (mcp.run() would hide the app from us)
    app = mcp.streamable_http_app()
    app.add_middleware(_AuthGate)
    uvicorn.run(
        app,
        host=os.environ.get("LINKVERSITY_MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("LINKVERSITY_MCP_PORT", "8001")),
    )
