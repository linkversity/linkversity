import json
import os

from flask import url_for
from flask import redirect
from flask import flash

# from flask import request
from flask import Blueprint
from flask import render_template
from flask import session
from flask import request
from flask import flash

#
from shopyo.api.html import notify
# from shopyo.api.forms import flash_errors
# from shopyo.api.enhance import get_active_theme_dir
# from shopyo.api.enhance import get_setting

# from modules.box__ecommerce.shop.helpers import get_cart_data

from flask_login import current_user
from flask_login import login_required
from sqlalchemy import func

from modules.box__linkolearn.linkolearn.models import Path
from modules.box__linkolearn.linkolearn.models import Link
from modules.box__linkolearn.linkolearn.models import ActivationCode
from modules.box__default.auth.models import User
from flask import jsonify
from init import db, csrf

dirpath = os.path.dirname(os.path.abspath(__file__))
module_info = {}

with open(dirpath + "/info.json") as f:
    module_info = json.load(f)


globals()["{}_blueprint".format(module_info["module_name"])] = Blueprint(
    "{}".format(module_info["module_name"]),
    __name__,
    template_folder="",
    url_prefix=module_info["url_prefix"],
)


module_blueprint = globals()["{}_blueprint".format(module_info["module_name"])]


@module_blueprint.route("/")
def index():
    # cant be defined above but must be manually set each time
    # active_theme_dir = os.path.join(
    #     dirpath, "..", "..", "themes", get_setting("ACTIVE_FRONT_THEME")
    # )
    # module_blueprint.template_folder = active_theme_dir

    # return str(module_blueprint.template_folder)
    def get_last_5():
        try:
            paths = Path.query.all()
            paths = [p for p in paths if p.is_visible]
            if len(paths) >= 10:
                return paths[-11:-1]
            else:
                len_paths = len(paths) + 1
                return paths[:len_paths]
        except:
            return []

    context = {"get_last_5": get_last_5, "current_user": current_user}

    return render_template("linkolearn_theme/index.html", **context)


@module_blueprint.route("/<username>")
def user_profile(username):
    from modules.box__linkolearn.linkolearn.models import Path

    context = {}
    user = User.query.filter(
        func.lower(User.username) == func.lower(username)
    ).first_or_404()
    context.update({"user": user})
    private_count = Path.query.filter_by(user_id=user.id, is_visible=False).count()
    context.update({"private_count": private_count})

    if user.is_enterprise() and user.team_id:
        from modules.box__default.auth.models import EnterpriseTeam
        from modules.box__linkolearn.linkolearn.enterprise_features import (
            EnterpriseTeamMember,
        )

        team = EnterpriseTeam.query.get(user.team_id)
        if team:
            members = EnterpriseTeamMember.query.filter_by(team_id=user.team_id).all()
            for m in members:
                m.user = User.query.get(m.user_id)
            team_paths = Path.query.filter_by(team_id=user.team_id).all()
            for p in team_paths:
                p.owner = User.query.get(p.user_id)
            team.paths = team_paths
            context.update(
                {
                    "team": team,
                    "team_members": members,
                    "is_team_owner": user == User.query.get(team.owner_id),
                }
            )

    return render_template("linkolearn_theme/templates/profile.html", **context)


def _check_path_access(path):
    """Flash+redirect when a non-visible path may not be shown, else None."""
    if path.is_visible:
        return None
    if current_user.is_authenticated:
        if (
            path.path_user == current_user
            or current_user in path.editors
            or path.is_org_member(current_user)
        ):
            return None
        if path.is_password_protected:
            return None
    elif path.is_password_protected:
        return None
    flash(notify("Path not public!", alert_type="warning"))
    return redirect(url_for("www.index"))


def _render_path(path):
    context = {}

    url = path.get_url().replace("/", "_")
    has_entered_password = session.get(f"has_entered_password_{url}", False)

    if path.team_id:
        from modules.box__default.auth.models import EnterpriseTeam
        from modules.box__linkolearn.linkolearn.enterprise_features import (
            EnterpriseTeamMember,
        )

        team = EnterpriseTeam.query.get(path.team_id)
        members = EnterpriseTeamMember.query.filter_by(team_id=path.team_id).all()
        for m in members:
            m.user = User.query.get(m.user_id)
        is_team_member = (
            current_user.is_authenticated and current_user.team_id == path.team_id
        )
        context.update(
            {
                "team": team,
                "team_members": members,
                "is_team_member": is_team_member,
            }
        )

    context.update(
        {
            "user": path.path_user,
            "path": path,
            "has_entered_password": has_entered_password,
            "session": session,
        }
    )
    return render_template("linkolearn_theme/templates/path.html", **context)


@module_blueprint.route("/<username>/<path_slug>")
def path(username, path_slug):
    user = User.query.filter(
        func.lower(User.username) == func.lower(username)
    ).first_or_404()
    path = Path.query.filter(
        Path.slug == path_slug, Path.user_id == user.id
    ).first_or_404()
    denied = _check_path_access(path)
    if denied:
        return denied

    # org-linked paths have a canonical /org/<org>/<slug> address
    if path.team_id:
        from modules.box__default.auth.models import EnterpriseTeam

        team = EnterpriseTeam.query.get(path.team_id)
        if team and team.slug:
            return redirect(
                url_for(
                    "www.org_path", org_slug=team.slug, path_slug=path.slug
                )
            )

    return _render_path(path)


@module_blueprint.route("/org/<org_slug>/<path_slug>")
def org_path(org_slug, path_slug):
    from modules.box__default.auth.models import EnterpriseTeam

    org = EnterpriseTeam.query.filter_by(slug=org_slug).first_or_404()
    path = Path.query.filter(
        Path.slug == path_slug, Path.team_id == org.id
    ).first_or_404()
    denied = _check_path_access(path)
    if denied:
        return denied
    return _render_path(path)


@module_blueprint.route("/privacy-policy")
def privacy_policy():
    return render_template("linkolearn_theme/templates/info/privacy_policy.html")


@module_blueprint.route("/contact")
def contact():
    return render_template("linkolearn_theme/templates/info/contact.html")


@module_blueprint.route("/about")
def about():
    return render_template("linkolearn_theme/templates/info/about.html")


@module_blueprint.route("/info")
def info():
    return render_template("linkolearn_theme/templates/info.html")


@module_blueprint.route("/org/<slug>")
def org_page(slug):
    from modules.box__default.auth.models import EnterpriseTeam

    org = EnterpriseTeam.query.filter_by(slug=slug).first_or_404()
    owner = User.query.get(org.owner_id)
    public_paths = Path.query.filter_by(team_id=org.id, is_visible=True).all()
    for p in public_paths:
        p.owner = User.query.get(p.user_id)

    can_create = False
    can_manage = False
    if current_user.is_authenticated:
        from modules.box__linkolearn.linkolearn.view import (
            _authorized_org,
            user_organizations,
        )

        can_create = org.id in [o.id for o in user_organizations(current_user)]
        can_manage = _authorized_org(org.id) is not None

    return render_template(
        "linkolearn_theme/templates/org.html",
        org=org,
        owner=owner,
        public_paths=public_paths,
        can_create=can_create,
        can_manage=can_manage,
    )


@module_blueprint.route("/org/<slug>/settings")
@login_required
def org_settings(slug):
    """Members management and logo for one organization, owner/admin only."""
    from modules.box__default.auth.models import EnterpriseTeam
    from modules.box__linkolearn.linkolearn.enterprise_features import (
        EnterpriseAnalytics,
        EnterpriseCustomDomain,
        EnterpriseTeamMember,
    )
    from modules.box__linkolearn.linkolearn.view import _authorized_org

    org = EnterpriseTeam.query.filter_by(slug=slug).first_or_404()
    if _authorized_org(org.id) is None:
        flash("Insufficient permission", "warning")
        return redirect(url_for("www.org_page", slug=slug))

    owner = User.query.get(org.owner_id)
    members = EnterpriseTeamMember.query.filter_by(team_id=org.id).all()
    for m in members:
        m.user = User.query.get(m.user_id)
    analytics = (
        EnterpriseAnalytics.query.filter_by(team_id=org.id)
        .order_by(EnterpriseAnalytics.event_date.desc())
        .limit(30)
        .all()
    )
    domains = EnterpriseCustomDomain.query.filter_by(team_id=org.id).all()

    return render_template(
        "linkolearn_theme/templates/org_settings.html",
        org=org,
        owner=owner,
        members=members,
        analytics=analytics,
        domains=domains,
    )


import validators


@module_blueprint.route("/save-link", methods=["GET", "POST"])
@login_required
def save_link():
    context = {"user": current_user}
    if request.method == "POST":
        data = request.form

        url = data.get("url")
        section_id = data.get("section_id")
        print(url, section_id)
        if not url or not section_id:
            return "URL and section ID are required"

        if not validators.url(url):
            return "Not valid url"

        # Save the link to the database
        new_link = Link(url=url, section_id=section_id)
        db.session.add(new_link)
        db.session.commit()

        profile_url = current_user.get_profile_url()
        return f"Link <{url}> saved successfully <a href='{profile_url}'>Return to profile</a>"
    return render_template("linkolearn_theme/templates/save_link.html", **context)


@module_blueprint.route("/activate", methods=["GET", "POST"])
def activate():
    from modules.www import dodo

    # the pricing page is public; only activating a plan requires a session
    authenticated = current_user.is_authenticated
    context = {
        "current_user": current_user,
        "is_pro": bool(authenticated and current_user.is_pro()),
        "is_enterprise": bool(authenticated and current_user.is_enterprise()),
        "dodo_configured": dodo.is_configured(),
        "dodo_enterprise_configured": bool(
            os.environ.get("DODO_PAYMENTS_API_KEY")
            and os.environ.get("DODO_PRODUCT_ID_ENTERPRISE")
        ),
    }
    if request.method == "POST":
        if not authenticated:
            return redirect(url_for("auth.login", next="/activate"))
        activation_code = request.form.get("code")

        code_entry = ActivationCode.query.filter_by(code=activation_code).first()

        if not code_entry:
            flash("Wrong code", "error")
            return redirect(url_for("www.activate"))

        current_user.subscription_plan = code_entry.plan_type
        db.session.commit()

        flash(f"Activated {code_entry.plan_type_name}!", "success")
        return redirect(url_for("www.activate"))

    return render_template("linkolearn_theme/templates/activate.html", **context)


@module_blueprint.route("/dodo/checkout", methods=["POST"])
@login_required
def dodo_checkout():
    from modules.www import dodo

    if not dodo.is_configured():
        return jsonify(
            {"error": "Payments are not configured yet "
                      "(DODO_PAYMENTS_API_KEY / DODO_PRODUCT_ID_PRO)"}
        ), 503

    plan = request.form.get("plan", type=int, default=dodo.PRO_PLAN)
    if plan not in (dodo.PRO_PLAN, dodo.ENTERPRISE_PLAN):
        plan = dodo.PRO_PLAN
    try:
        checkout_url = dodo.create_checkout(current_user, plan=plan)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"checkout_url": checkout_url})


@module_blueprint.route("/dodo/return", methods=["GET"])
@login_required
def dodo_return():
    # Dodo redirects here with payment_id/subscription_id/status query
    # params. Fulfillment happens exclusively from the signed webhook —
    # this page only acknowledges the redirect.
    plan = request.args.get("plan", "1")
    plan_name = "Enterprise" if plan == "2" else "Pro"
    if request.args.get("status") == "succeeded":
        flash(f"Payment received: activating your {plan_name} plan…", "success")
    else:
        flash("Checkout finished: we'll activate your plan as soon as the "
              "payment is confirmed.", "info")
    return redirect(url_for("www.activate"))


@module_blueprint.route("/dodo/webhook", methods=["POST"])
@csrf.exempt
def dodo_webhook():
    from modules.www import dodo

    # raw bytes exactly as received — the signature covers them
    raw_body = request.get_data()
    headers = {
        "webhook-id": request.headers.get("webhook-id", ""),
        "webhook-signature": request.headers.get("webhook-signature", ""),
        "webhook-timestamp": request.headers.get("webhook-timestamp", ""),
    }
    try:
        event = dodo.verify_webhook(raw_body, headers)
    except Exception:
        return jsonify({"error": "Invalid signature"}), 401

    try:
        result = dodo.fulfill_event(event)
        if result:
            print(f"[dodo webhook] {result}")
    except Exception as e:
        # acknowledge anyway: Dodo retries failed (non-2xx) deliveries, but
        # a fulfillment error shouldn't loop forever either
        print(f"[dodo webhook] fulfillment error: {e}")

    return jsonify({"received": True})
