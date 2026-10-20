"""Linkversity MCP server (standalone process).

Runs separately from Flask and calls the Linkversity REST API over HTTP:

    export LINKVERSITY_API_URL="https://linkversity.lol"
    python server.py          # streamable-http on 0.0.0.0:8001/mcp

If the incoming MCP request carries an Authorization: Bearer header, it is
forwarded to the Flask API so personal tools see the connected user.
"""

import os

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
        "Discover Linkversity collections and build study plans. Use "
        "search_public_collections to find public collections by topic, "
        "get_public_collection / get_collection_links to read their contents, "
        "list_my_collections + get_collection_links for a connected account, "
        "and create_study_plan to fetch a collection's resources in a study "
        "sequence for a given experience level and weekly time budget. "
        "Every resource includes the Linkversity source URL - cite it."
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


@mcp.tool(annotations=_READONLY)
def create_study_plan(
    collection_id: int,
    experience_level: str = "beginner",
    hours_per_week: int = 5,
    ctx: Context | None = None,
) -> dict:
    """Fetch a Linkversity collection's resources sequenced for a study plan.

    Retrieve the resources here, then write the actual plan yourself: order
    the sections, spread them across the requested hours_per_week, and tailor
    the explanations to the experience_level. This is read-only - it never
    modifies the collection.
    """
    payload = {
        "experience_level": experience_level,
        "hours_per_week": hours_per_week,
    }
    result = _post(
        f"/api/v1/me/collections/{collection_id}/study-plan", payload, ctx
    )
    if "error" not in result:
        return result
    # not connected / not authorized -> fall back to public links
    links = get_collection_links(collection_id, ctx=ctx)
    return {
        "collection_id": collection_id,
        "experience_level": experience_level,
        "hours_per_week": hours_per_week,
        "fallback": True,
        "links": links,
    }


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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
