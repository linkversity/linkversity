"""
Linkversity API v1 — backing API for the ChatGPT/MCP integration.

Implements the endpoints the MCP server calls:

    GET  /api/v1/public/collections            search public collections
    GET  /api/v1/public/collections/<id>       one public collection
    GET  /api/v1/public/collections/<id>/links links in a public collection
    GET  /api/v1/me/collections                connected user's collections
    GET  /api/v1/me/collections/<id>/links     links the user may access
    POST /api/v1/me/collections/<id>/study-plan prepare resources for a plan
    GET  /api/v1/integrations/status           integration/connection status

Access rules mirror the web UI (`www._check_path_access`):

    public      -> is_visible
    links       -> is_visible and NOT password-protected
    protected   -> owner / editor / org member (Path.can_edit)
"""

import time
from collections import defaultdict, deque

from flask import Blueprint, jsonify, request
from flask_login import current_user  # noqa: F401  (available for future use)

from modules.box__default.auth.models import User
from modules.box__linkolearn.linkolearn.models import Link, Path, Section

from init import db, csrf

# shopyo's module loader looks up {module_name}_blueprint
apiv1_blueprint = Blueprint("apiv1", __name__, url_prefix="/api/v1")

# OAuth + discovery routes live at the app root (/oauth/*, /.well-known/*);
# register them on the app once this blueprint is installed.
from modules.box__linkolearn.apiv1.oauth import (  # noqa: E402
    aux_blueprint,
    wellknown_blueprint,
)


@apiv1_blueprint.record_once
def _register_aux(state):
    state.app.register_blueprint(wellknown_blueprint)
    state.app.register_blueprint(aux_blueprint)


# --------------------------------------------------------------------------
# auth helpers
# --------------------------------------------------------------------------

def _bearer_token():
    """Token from Authorization: Bearer <t> / X-API-Token / ?token=."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.headers.get("X-API-Token") or request.args.get("token")


def _user_from_token(token, scope="collections:read"):
    """Resolve a user from a raw token. Never trusts a supplied user id.

    Accepts OAuth access tokens (ChatGPT connected account), the legacy
    ``api_token`` column and hashed ``UserToken`` rows (personal API keys).
    OAuth tokens must carry the requested scope; legacy personal-API tokens
    are full-access (owner-controlled, equivalent to a password).
    """
    if not token:
        return None
    # OAuth access token issued by /oauth/token
    from modules.box__linkolearn.apiv1.oauth import resolve_oauth_token

    user, scopes = resolve_oauth_token(token)
    if user is not None:
        if scope not in (scopes or "").split():
            return None  # valid token, insufficient scope
        return user
    # legacy single api_token column
    user = User.query.filter_by(api_token=token).first()
    if user:
        return user
    # hashed UserToken table (shopyo_auth)
    try:
        return User.verify_api_token(token)
    except Exception:
        return None


def _require_user(scope="collections:read"):
    """Return (user, None) when the token grants `scope`, else (None, error)."""
    user = _user_from_token(_bearer_token(), scope)
    if user is None:
        # distinguish bad token from missing scope on OAuth tokens
        from modules.box__linkolearn.apiv1.oauth import resolve_oauth_token

        tok = _bearer_token()
        if tok:
            holder, scopes = resolve_oauth_token(tok)
            if holder is not None:
                return None, (
                    jsonify(
                        {
                            "error": "insufficient_scope",
                            "required_scope": scope,
                            "granted_scopes": (scopes or "").split(),
                        }
                    ),
                    403,
                )
        return None, (jsonify({"error": "invalid or missing access token"}), 401)
    return user, None


# --------------------------------------------------------------------------
# rate limiting (per-token, in-memory fixed window)
# --------------------------------------------------------------------------

_RATE_LIMIT = 120          # requests per window
_RATE_WINDOW = 60          # seconds
_rate_hits = defaultdict(deque)


def _rate_limited(key):
    now = time.time()
    hits = _rate_hits[key]
    while hits and now - hits[0] > _RATE_WINDOW:
        hits.popleft()
    if len(hits) >= _RATE_LIMIT:
        return True
    hits.append(now)
    return False


def _enforce_rate_limit():
    key = _bearer_token() or (request.remote_addr or "anon")
    if _rate_limited(key):
        return jsonify({"error": "rate limit exceeded"}), 429
    return None


# --------------------------------------------------------------------------
# serialization
# --------------------------------------------------------------------------

def _pagination():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    page = max(page, 1)
    per_page = min(max(per_page, 1), 50)
    return page, per_page


def _public(path):
    """Public-safe metadata for a collection."""
    return {
        "id": path.id,
        "title": path.title,
        "slug": path.slug,
        "url": request.host_url.rstrip("/") + path.get_url(),
        "owner": path.path_user.username if path.path_user else None,
        "is_password_protected": bool(path.is_password_protected),
        "section_count": len(path.sections),
        "link_count": sum(len(s.links) for s in path.sections),
        "description": _description(path),
    }


def _description(path):
    """Best-effort collection description from its section titles."""
    titles = [s.title for s in path.sections if s.title]
    if not titles:
        return None
    return "Covers " + ", ".join(titles[:6]) + ("..." if len(titles) > 6 else "")


def _link_resource(link):
    """A single resource with a link back to Linkversity."""
    section = link.link_section
    return {
        "id": link.id,
        "title": link.title or link.url,
        "url": link.get_url(),
        "description": link.description,
        "image_url": link.image_url,
        "section": section.title if section else None,
        "source": request.host_url.rstrip("/")
        + (section.section_path.get_url() if section else ""),
    }


# --------------------------------------------------------------------------
# query helpers
# --------------------------------------------------------------------------

def _public_query():
    return Path.query.filter_by(is_visible=True)


def _can_read_links(path, user):
    if user is not None:
        try:
            if path.can_edit(user):
                return True
        except Exception:
            pass
    return bool(path.is_visible) and not bool(path.is_password_protected)


# --------------------------------------------------------------------------
# public endpoints
# --------------------------------------------------------------------------

@apiv1_blueprint.route("/public/collections", methods=["GET"])
@csrf.exempt
def public_collections():
    limited = _enforce_rate_limit()
    if limited:
        return limited

    page, per_page = _pagination()
    query = (request.args.get("q") or request.args.get("query") or "").strip()

    stmt = _public_query()
    if query:
        like = f"%{query}%"
        section_ids = db.session.query(Section.path_id).filter(
            Section.title.ilike(like)
        )
        stmt = stmt.filter(
            db.or_(
                Path.title.ilike(like),
                Path.slug.ilike(like),
                Path.id.in_(section_ids),
            )
        )

    pagination = stmt.order_by(Path.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "items": [_public(p) for p in pagination.items],
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "has_more": pagination.has_next,
        }
    )


@apiv1_blueprint.route("/public/collections/<int:collection_id>", methods=["GET"])
@csrf.exempt
def public_collection(collection_id):
    limited = _enforce_rate_limit()
    if limited:
        return limited

    path = Path.query.get(collection_id)
    if path is None or not path.is_visible:
        return jsonify({"error": "collection not found"}), 404
    return jsonify(_public(path))


@apiv1_blueprint.route(
    "/public/collections/<int:collection_id>/links", methods=["GET"]
)
@csrf.exempt
def public_collection_links(collection_id):
    limited = _enforce_rate_limit()
    if limited:
        return limited

    path = Path.query.get(collection_id)
    if path is None or not path.is_visible:
        return jsonify({"error": "collection not found"}), 404
    if path.is_password_protected:
        return jsonify({"error": "collection is password-protected"}), 403

    page, per_page = _pagination()

    link_ids = (
        db.session.query(Link.id)
        .join(Section, Link.section_id == Section.id)
        .filter(Section.path_id == path.id)
        .order_by(Section.id.asc(), Link.id.asc())
        .all()
    )
    ids = [r[0] for r in link_ids]
    total = len(ids)
    start = (page - 1) * per_page
    page_ids = ids[start : start + per_page]
    links = Link.query.filter(Link.id.in_(page_ids)).all() if page_ids else []
    order = {lid: i for i, lid in enumerate(page_ids)}
    links.sort(key=lambda l: order.get(l.id, 0))

    return jsonify(
        {
            "items": [_link_resource(l) for l in links],
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": start + per_page < total,
        }
    )


# --------------------------------------------------------------------------
# authenticated (connected-account) endpoints
# --------------------------------------------------------------------------

def _owned_query(user):
    """Collections the connected user owns or can edit.

    Mirrors Path.can_edit(): owner, explicit editor, org owner, or
    org member with an admin/member role.
    """
    from modules.box__default.auth.models import EnterpriseTeam
    from modules.box__linkolearn.linkolearn.enterprise_features import (
        EnterpriseTeamMember,
    )

    # teams the user owns
    owned_team_ids = [
        t.id
        for t in EnterpriseTeam.query.filter_by(owner_id=user.id).all()
    ]

    # teams where the user is an admin/member (viewer excluded, as in can_edit)
    member_team_ids = [
        m.team_id
        for m in EnterpriseTeamMember.query.filter_by(user_id=user.id).all()
        if m.role in ("admin", "member")
    ]

    team_ids = list(set(owned_team_ids + member_team_ids))

    conditions = [Path.user_id == user.id, Path.editors.any(User.id == user.id)]
    if team_ids:
        conditions.append(Path.team_id.in_(team_ids))

    return Path.query.filter(db.or_(*conditions))


@apiv1_blueprint.route("/me/collections", methods=["GET"])
@csrf.exempt
def me_collections():
    limited = _enforce_rate_limit()
    if limited:
        return limited

    user, err = _require_user()
    if err:
        return err

    page, per_page = _pagination()
    query = (request.args.get("q") or "").strip()

    stmt = _owned_query(user)
    if query:
        like = f"%{query}%"
        stmt = stmt.filter(db.or_(Path.title.ilike(like), Path.slug.ilike(like)))

    pagination = stmt.order_by(Path.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items = []
    for p in pagination.items:
        item = _public(p)
        item["is_public"] = bool(p.is_visible)
        item["can_edit"] = True
        items.append(item)

    return jsonify(
        {
            "items": items,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "has_more": pagination.has_next,
        }
    )


@apiv1_blueprint.route(
    "/me/collections/<int:collection_id>/links", methods=["GET"]
)
@csrf.exempt
def me_collection_links(collection_id):
    limited = _enforce_rate_limit()
    if limited:
        return limited

    user, err = _require_user()
    if err:
        return err

    path = Path.query.get(collection_id)
    if path is None:
        return jsonify({"error": "collection not found"}), 404
    if not _can_read_links(path, user):
        return jsonify({"error": "access denied"}), 403

    page, per_page = _pagination()

    link_ids = (
        db.session.query(Link.id)
        .join(Section, Link.section_id == Section.id)
        .filter(Section.path_id == path.id)
        .order_by(Section.id.asc(), Link.id.asc())
        .all()
    )
    ids = [r[0] for r in link_ids]
    total = len(ids)
    start = (page - 1) * per_page
    page_ids = ids[start : start + per_page]
    links = Link.query.filter(Link.id.in_(page_ids)).all() if page_ids else []
    order = {lid: i for i, lid in enumerate(page_ids)}
    links.sort(key=lambda l: order.get(l.id, 0))

    return jsonify(
        {
            "items": [_link_resource(l) for l in links],
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": start + per_page < total,
        }
    )


@apiv1_blueprint.route(
    "/me/collections/<int:collection_id>/study-plan", methods=["POST"]
)
@csrf.exempt
def me_study_plan(collection_id):
    """Read-only: order a collection's resources into a study sequence.

    Does NOT modify the collection. Returns the resources grouped by section
    so the model can assemble a plan.
    """
    limited = _enforce_rate_limit()
    if limited:
        return limited

    user, err = _require_user()
    if err:
        return err

    path = Path.query.get(collection_id)
    if path is None:
        return jsonify({"error": "collection not found"}), 404
    if not _can_read_links(path, user):
        return jsonify({"error": "access denied"}), 403

    data = request.get_json(silent=True) or {}
    level = str(data.get("experience_level") or "beginner").strip()[:40]
    hours = data.get("hours_per_week")

    sections = []
    total_links = 0
    for section in path.sections:
        resources = [_link_resource(l) for l in section.links]
        total_links += len(resources)
        sections.append(
            {
                "section": section.title,
                "order": len(sections) + 1,
                "links": resources,
            }
        )

    return jsonify(
        {
            "collection": _public(path),
            "experience_level": level,
            "hours_per_week": hours,
            "sections": sections,
            "total_links": total_links,
            "note": "resources only; no changes were made to the collection",
        }
    )


# --------------------------------------------------------------------------
# write endpoints (connected account, collections:write scope)
# --------------------------------------------------------------------------


@apiv1_blueprint.route("/me/collections", methods=["POST"])
@csrf.exempt
def me_create_collection():
    """Create a new personal collection (write tool: create_collection)."""
    limited = _enforce_rate_limit()
    if limited:
        return limited

    user, err = _require_user("collections:write")
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    if not title or len(title) > 200:
        return jsonify({"error": "title is required (max 200 chars)"}), 400

    # unique slug: base, then -2, -3, ...
    base = Path.slugify(title) or "collection"
    slug = base
    n = 2
    while Path.query.filter_by(user_id=user.id, slug=slug).first() is not None:
        slug = f"{base}-{n}"
        n += 1

    path = Path(
        title=title,
        slug=slug,
        user_id=user.id,
        # private by default; the user controls visibility on the site
        is_visible=bool(data.get("is_public", False)),
    )
    if data.get("section_title"):
        path.sections.append(Section(title=str(data["section_title"]).strip()[:200]))
    db.session.add(path)
    db.session.commit()

    resp = _public(path)
    resp["section"] = "created"
    return jsonify(resp), 201


@apiv1_blueprint.route(
    "/me/collections/<int:collection_id>/links", methods=["POST"]
)
@csrf.exempt
def me_save_link(collection_id):
    """Save a link into one of the user's collections (write: save_link).

    Body: {url, section_title?} - section created if it doesn't exist;
    defaults to the collection's first section.
    """
    import validators

    limited = _enforce_rate_limit()
    if limited:
        return limited

    user, err = _require_user("collections:write")
    if err:
        return err

    path = Path.query.get(collection_id)
    if path is None:
        return jsonify({"error": "collection not found"}), 404
    if not path.can_edit(user):
        return jsonify({"error": "access denied"}), 403

    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()
    if not url or not validators.url(url):
        return jsonify({"error": "url is required and must be a valid URL"}), 400
    if len(url) > 500:
        return jsonify({"error": "url too long (max 500)"}), 400

    # resolve section: by title (create on demand), else first section
    section = None
    section_title = str(data.get("section_title") or "").strip()
    if section_title:
        section = next(
            (s for s in path.sections if (s.title or "").lower() == section_title.lower()),
            None,
        )
        if section is None:
            section = Section(title=section_title[:200], path_id=path.id)
            db.session.add(section)
            db.session.flush()
    if section is None:
        section = next((s for s in path.sections), None)
    if section is None:
        return jsonify({"error": "collection has no section; pass section_title"}), 400

    # de-dup: same URL already in this collection?
    existing = Link.query.filter_by(section_id=section.id, url=url).first()
    if existing is None:
        for s in path.sections:  # also check sibling sections
            for l in s.links:
                if l.url == url:
                    existing = l
                    break
            if existing:
                break
    if existing is not None:
        return (
            jsonify(
                {
                    "link": _link_resource(existing),
                    "note": "already in this collection",
                }
            ),
            200,
        )

    link = Link(
        url=url,
        section_id=section.id,
        title=(str(data.get("title") or "").strip()[:500] or None),
        description=(str(data.get("description") or "").strip() or None),
    )
    db.session.add(link)
    db.session.commit()

    return jsonify({"link": _link_resource(link), "note": "saved"}), 201


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

@apiv1_blueprint.route("/integrations/status", methods=["GET"])
@csrf.exempt
def integrations_status():
    token = _bearer_token()
    user = _user_from_token(token)
    return jsonify(
        {
            "integration": "chatgpt",
            "api_version": "v1",
            "authenticated": user is not None,
            "user": (user.username if user else None),
            "scopes": ["collections:read", "links:read"] if user else [],
            "endpoints": [
                "/api/v1/public/collections",
                "/api/v1/public/collections/{id}",
                "/api/v1/public/collections/{id}/links",
                "/api/v1/me/collections",
                "/api/v1/me/collections/{id}/links",
                "/api/v1/me/collections/{id}/study-plan",
                "/api/v1/integrations/status",
            ],
        }
    )
