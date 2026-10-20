"""OAuth 2.0 for the Linkversity API (ChatGPT connected accounts).

Implements a compact RFC 6749 authorization-code flow with PKCE (S256),
RFC 7591 dynamic client registration, refresh tokens and bearer userinfo.

    GET  /.well-known/oauth-authorization-server   discovery metadata
    GET  /.well-known/oauth-protected-resource     resource metadata
    POST /oauth/register                           dynamic client registration
    GET  /oauth/authorize                          consent screen (login required)
    POST /oauth/authorize                          approve/deny
    POST /oauth/token                              code / refresh_token exchange
    GET  /oauth/userinfo                           identity for a bearer token

Access tokens resolve through the same ``Bearer`` header the rest of the API
already accepts, so the MCP server needs no changes - it just forwards them.
"""

import base64
import datetime
import hashlib
import json
import os
import secrets

from flask import Blueprint, jsonify, redirect, render_template_string, request
from flask_login import login_required
from shopyo.api.models import PkModel

from init import csrf, db

SCOPE_SUPPORTED = ["collections:read", "collections:write"]
ACCESS_TOKEN_TTL = datetime.timedelta(days=7)
REFRESH_TOKEN_TTL = datetime.timedelta(days=90)
AUTH_CODE_TTL = datetime.timedelta(minutes=5)


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class OAuthClient(PkModel):
    __tablename__ = "oauth_clients"

    client_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    client_secret_hash = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    redirect_uris = db.Column(db.Text, nullable=False, default="[]")  # JSON list
    token_endpoint_auth_method = db.Column(
        db.String(40), nullable=False, default="client_secret_post"
    )
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    def check_secret(self, secret: str) -> bool:
        return bool(secret) and _hash(secret) == self.client_secret_hash

    def allows_redirect(self, uri: str) -> bool:
        try:
            allowed = json.loads(self.redirect_uris or "[]")
        except ValueError:
            allowed = []
        return uri in allowed


class OAuthAuthorizationCode(PkModel):
    __tablename__ = "oauth_authorization_codes"

    code_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    client_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    scopes = db.Column(db.String(255), nullable=False, default="")
    redirect_uri = db.Column(db.Text, nullable=False)
    code_challenge = db.Column(db.String(128))
    code_challenge_method = db.Column(db.String(10))  # "S256" | "plain" | None
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)


class OAuthAccessToken(PkModel):
    __tablename__ = "oauth_access_tokens"

    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    client_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    scopes = db.Column(db.String(255), nullable=False, default="")
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    @property
    def expired(self) -> bool:
        return datetime.datetime.now() > self.expires_at


class OAuthRefreshToken(PkModel):
    __tablename__ = "oauth_refresh_tokens"

    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    client_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    scopes = db.Column(db.String(255), nullable=False, default="")
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)


# --------------------------------------------------------------------------
# token helpers (imported by the API view for scope checks)
# --------------------------------------------------------------------------


def resolve_oauth_token(token: str):
    """Return (user, scopes) for a valid OAuth access token, else (None, None)."""
    from modules.box__default.auth.models import User

    row = OAuthAccessToken.query.filter_by(token_hash=_hash(token)).first()
    if row is None or row.revoked or row.expired:
        return None, None
    user = User.query.get(row.user_id)
    return user, (row.scopes or "")


def _issue_tokens(user_id: int, client_id: str, scopes: str):
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(32)
    OAuthAccessToken.create(
        token_hash=_hash(access),
        client_id=client_id,
        user_id=user_id,
        scopes=scopes,
        expires_at=datetime.datetime.now() + ACCESS_TOKEN_TTL,
    )
    OAuthRefreshToken.create(
        token_hash=_hash(refresh),
        client_id=client_id,
        user_id=user_id,
        scopes=scopes,
        expires_at=datetime.datetime.now() + REFRESH_TOKEN_TTL,
    )
    return access, refresh


def _parse_scopes(raw: str):
    return [s for s in (raw or "").split() if s in SCOPE_SUPPORTED]


# --------------------------------------------------------------------------
# discovery metadata (registered on the root, outside /api/v1)
# --------------------------------------------------------------------------

wellknown_blueprint = Blueprint("wellknown", __name__)


def _base_url() -> str:
    return request.host_url.rstrip("/")


@wellknown_blueprint.route("/.well-known/oauth-authorization-server")
@csrf.exempt
def oauth_metadata():
    base = _base_url()
    return jsonify(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "userinfo_endpoint": f"{base}/oauth/userinfo",
            "scopes_supported": SCOPE_SUPPORTED,
            "response_types_supported": ["code"],
            "response_modes_supported": ["query"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
                "client_secret_basic",
            ],
        }
    )


@wellknown_blueprint.route("/.well-known/oauth-protected-resource")
@csrf.exempt
def protected_resource_metadata():
    base = _base_url()
    return jsonify(
        {
            "resource": f"{base}/api/v1",
            "authorization_servers": [base],
            "scopes_supported": SCOPE_SUPPORTED,
            "bearer_methods_supported": ["header"],
        }
    )


# OpenAI plugin-domain verification challenge. The portal requires the exact
# token as plain text at the origin-root well-known URL (not JSON).
# Set the token on the server, never commit it:
#   Environment="LINKVERSITY_OPENAI_CHALLENGE_TOKEN=<token from the portal>"
_OPENAI_CHALLENGE_TOKEN = os.environ.get("LINKVERSITY_OPENAI_CHALLENGE_TOKEN", "")


@wellknown_blueprint.route("/.well-known/openai-apps-challenge")
@csrf.exempt
def openai_apps_challenge():
    if not _OPENAI_CHALLENGE_TOKEN:
        return "Not configured", 404
    return _OPENAI_CHALLENGE_TOKEN, 200, {"Content-Type": "text/plain"}


# --------------------------------------------------------------------------
# dynamic client registration (RFC 7591)
# --------------------------------------------------------------------------


# aux routes live outside /api/v1; apiv1's view registers this blueprint
aux_blueprint = Blueprint("oauth_aux", __name__)


@aux_blueprint.route("/oauth/register", methods=["POST"])
@csrf.exempt
def register_client():
    data = request.get_json(silent=True) or {}
    redirect_uris = data.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return jsonify({"error": "invalid_client_metadata"}), 400

    client_id = secrets.token_urlsafe(24)
    client_secret = secrets.token_urlsafe(32)
    OAuthClient.create(
        client_id=client_id,
        client_secret_hash=_hash(client_secret),
        name=str(data.get("client_name") or "Linkversity client")[:120],
        redirect_uris=json.dumps([str(u) for u in redirect_uris[:10]]),
    )
    return jsonify(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": int(datetime.datetime.now().timestamp()),
            "client_secret_expires_at": 0,  # never
            "client_name": data.get("client_name"),
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "client_secret_post",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }
    ), 201


def _client_from_request():
    """Client auth via client_secret_post body params or Basic auth."""
    import base64

    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    if not client_id and request.authorization:
        client_id = request.authorization.username
        client_secret = request.authorization.password
    if not client_id:
        return None
    client = OAuthClient.query.filter_by(client_id=client_id).first()
    if client is None or not client.check_secret(client_secret):
        return None
    return client


# --------------------------------------------------------------------------
# authorization endpoint (consent screen)
# --------------------------------------------------------------------------

_CONSENT_HTML = """<!doctype html>
<html><head><title>Connect Linkversity to {{ client.name }}</title>
<style>
 body{font-family:system-ui,sans-serif;background:#f6f6f7;display:flex;
      justify-content:center;padding-top:8vh;margin:0}
 .card{background:#fff;border-radius:14px;padding:2rem;max-width:420px;
       box-shadow:0 4px 24px rgba(0,0,0,.08)}
 h1{font-size:1.2rem;margin:0 0 .5rem}
 p{color:#555;font-size:.95rem;line-height:1.5}
 .scopes{background:#f6f6f7;border-radius:8px;padding:.8rem 1rem;
         font-size:.9rem;color:#333;margin:1rem 0}
 button{border:0;border-radius:999px;padding:.7rem 1.4rem;font-size:1rem;
        cursor:pointer;margin-right:.5rem}
 .ok{background:#eb6864;color:#fff}.no{background:#eee;color:#333}
</style></head><body>
<div class="card">
 <h1>{{ client.name }} wants to access your Linkversity account</h1>
 <p>This will let {{ client.name }}:</p>
 <div class="scopes">
   &#8226; Read your collections and the links inside them<br>
   &#8226; Save new links and create collections on your behalf<br>
   &#8226; Build study plans from your saved resources
 </div>
 <p style="font-size:.85rem">Scope: <code>{{ scope }}</code></p>
 <form method="post" style="display:inline">
  {% for k, v in hidden.items() %}<input type="hidden" name="{{k}}" value="{{v}}">{% endfor %}
  <button class="ok" name="decision" value="approve">Allow</button>
  <button class="no" name="decision" value="deny">Cancel</button>
 </form>
</div></body></html>"""


@aux_blueprint.route("/oauth/authorize", methods=["GET"])
@login_required
def authorize_get():
    args = request.args
    if args.get("response_type") != "code":
        return jsonify({"error": "unsupported_response_type"}), 400
    client = OAuthClient.query.filter_by(
        client_id=args.get("client_id", "")
    ).first()
    redirect_uri = args.get("redirect_uri", "")
    if client is None or not client.allows_redirect(redirect_uri):
        return jsonify({"error": "invalid_request"}), 400

    scopes = " ".join(_parse_scopes(args.get("scope", "")))
    hidden = {
        "client_id": client.client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": args.get("state", ""),
    }
    for pkce_key in ("code_challenge", "code_challenge_method"):
        if args.get(pkce_key):
            hidden[pkce_key] = args[pkce_key]
    return render_template_string(_CONSENT_HTML, client=client, scope=scopes, hidden=hidden)


@aux_blueprint.route("/oauth/authorize", methods=["POST"])
@login_required
@csrf.exempt
def authorize_post():
    from flask_login import current_user

    form = request.form
    redirect_uri = form.get("redirect_uri", "")

    def _redirect_error(err):
        from urllib.parse import urlencode

        q = {"error": err}
        if form.get("state"):
            q["state"] = form["state"]
        sep = "&" if "?" in redirect_uri else "?"
        return redirect(f"{redirect_uri}{sep}{urlencode(q)}")

    client = OAuthClient.query.filter_by(client_id=form.get("client_id", "")).first()
    if client is None or not client.allows_redirect(redirect_uri):
        return jsonify({"error": "invalid_request"}), 400

    if form.get("decision") != "approve":
        return _redirect_error("access_denied")

    code = secrets.token_urlsafe(32)
    OAuthAuthorizationCode.create(
        code_hash=_hash(code),
        client_id=client.client_id,
        user_id=current_user.id,
        scopes=form.get("scope", ""),
        redirect_uri=redirect_uri,
        code_challenge=form.get("code_challenge"),
        code_challenge_method=form.get("code_challenge_method"),
        expires_at=datetime.datetime.now() + AUTH_CODE_TTL,
    )
    from urllib.parse import urlencode

    q = {"code": code}
    if form.get("state"):
        q["state"] = form["state"]
    sep = "&" if "?" in redirect_uri else "?"
    return redirect(f"{redirect_uri}{sep}{urlencode(q)}")


# --------------------------------------------------------------------------
# token endpoint
# --------------------------------------------------------------------------


@aux_blueprint.route("/oauth/token", methods=["POST"])
@csrf.exempt
def token():
    client = _client_from_request()
    if client is None:
        return jsonify({"error": "invalid_client"}), 401

    grant_type = request.form.get("grant_type")

    if grant_type == "authorization_code":
        code = request.form.get("code", "")
        row = OAuthAuthorizationCode.query.filter_by(code_hash=_hash(code)).first()
        if (
            row is None
            or row.used
            or row.client_id != client.client_id
            or datetime.datetime.now() > row.expires_at
        ):
            return jsonify({"error": "invalid_grant"}), 400
        if row.redirect_uri != request.form.get("redirect_uri", ""):
            return jsonify({"error": "invalid_grant"}), 400

        # PKCE
        if row.code_challenge:
            verifier = request.form.get("code_verifier", "")
            if not verifier:
                return jsonify({"error": "invalid_grant"}), 400
            if row.code_challenge_method == "S256":
                computed = (
                    base64.urlsafe_b64encode(
                        hashlib.sha256(verifier.encode()).digest()
                    )
                    .rstrip(b"=")
                    .decode()
                )
            else:
                computed = verifier
            if computed != row.code_challenge:
                return jsonify({"error": "invalid_grant"}), 400

        row.used = True
        row.update()
        access, refresh = _issue_tokens(
            row.user_id, client.client_id, row.scopes or ""
        )
        return jsonify(
            {
                "access_token": access,
                "token_type": "Bearer",
                "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
                "refresh_token": refresh,
                "scope": row.scopes,
            }
        )

    if grant_type == "refresh_token":
        refresh = request.form.get("refresh_token", "")
        row = OAuthRefreshToken.query.filter_by(token_hash=_hash(refresh)).first()
        if (
            row is None
            or row.revoked
            or row.client_id != client.client_id
            or datetime.datetime.now() > row.expires_at
        ):
            return jsonify({"error": "invalid_grant"}), 400
        access, new_refresh = _issue_tokens(
            row.user_id, client.client_id, row.scopes or ""
        )
        row.revoked = True
        row.update()
        return jsonify(
            {
                "access_token": access,
                "token_type": "Bearer",
                "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
                "refresh_token": new_refresh,
                "scope": row.scopes,
            }
        )

    return jsonify({"error": "unsupported_grant_type"}), 400


# --------------------------------------------------------------------------
# userinfo
# --------------------------------------------------------------------------


@aux_blueprint.route("/oauth/userinfo", methods=["GET"])
@csrf.exempt
def userinfo():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return jsonify({"error": "invalid_token"}), 401
    user, scopes = resolve_oauth_token(auth[7:].strip())
    if user is None:
        return jsonify({"error": "invalid_token"}), 401
    return jsonify(
        {
            "sub": str(user.id),
            "username": user.username,
            "scopes": (scopes or "").split(),
        }
    )
