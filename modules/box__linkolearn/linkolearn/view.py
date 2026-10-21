from shopyo.api.module import ModuleHelp
import os
import uuid

from flask import render_template
from flask import url_for
from flask import redirect
from flask import flash
from flask import request
from flask import jsonify
from flask import session
from flask import current_app

# from shopyo.api.html import notify_success
# from shopyo.api.forms import flash_errors

from flask_login import login_required
from flask_login import current_user

from modules.box__default.auth.models import User
from modules.box__linkolearn.linkolearn.models import Path
from modules.box__linkolearn.linkolearn.models import Section
from modules.box__linkolearn.linkolearn.models import Link
from modules.box__linkolearn.linkolearn.models import LikeList
from modules.box__linkolearn.linkolearn.models import BookmarkList
from modules.box__linkolearn.linkolearn.models import Emoji
from modules.box__linkolearn.linkolearn.models import PATH_ICONS
from modules.box__linkolearn.linkolearn.models import PATH_ICON_CLASSES
from modules.box__linkolearn.linkolearn.enterprise_features import (
    EnterpriseAuditLog,
    EnterpriseAnalytics,
    EnterpriseTeamMember,
    EnterpriseCustomDomain,
)
from modules.box__default.auth.models import EnterpriseTeam
from modules.box__linkolearn.linkolearn.forms import ChangeNameForm
from modules.box__linkolearn.linkolearn.forms import ChangePasswordForm

from init import db

from shopyo.api.security import get_safe_redirect
from shopyo.api.forms import flash_errors
from shopyo.api.html import notify

import validators

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]


@module_blueprint.route("/")
@login_required
def index():
    return render_template("linkolearn/dashboard.html")


@module_blueprint.route("/dashboard")
@login_required
def dashboard():
    return render_template("linkolearn/dashboard.html")


@module_blueprint.route("/like/<path_id>", methods=["GET"])
@login_required
def toggle_like(path_id):
    path = Path.query.get(path_id)
    if path.like_list is None:
        path.like_list = LikeList()
        path.save()
    if current_user not in path.like_list.users:
        path.like_list.users.append(current_user)
    else:
        path.like_list.users.remove(current_user)
    path.save()
    if "next" in request.args:
        if request.args.get("next") != "":
            return redirect(get_safe_redirect(request.args.get("next")))
        else:
            return redirect(url_for("www.index"))
    else:
        return redirect(url_for("www.index"))


@module_blueprint.route("/bookmark/<path_id>", methods=["GET"])
@login_required
def toggle_bookmark(path_id):
    path = Path.query.get(path_id)
    if path.bookmark_list is None:
        path.bookmark_list = BookmarkList()
        path.save()
    if current_user not in path.bookmark_list.users:
        path.bookmark_list.users.append(current_user)
    else:
        path.bookmark_list.users.remove(current_user)
    path.save()
    if "next" in request.args:
        if request.args.get("next") != "":
            return redirect(get_safe_redirect(request.args.get("next")))
        else:
            return redirect(url_for("www.index"))
    else:
        return redirect(url_for("www.index"))


@module_blueprint.route("/password/<path_id>", methods=["POST"])
@login_required
def toggle_password(path_id):
    path = Path.query.get(path_id)

    if current_user == path.path_user:
        if path.is_password_protected in [False, None]:
            path.is_password_protected = True
            path.password = request.form.get("password")
            print(request.form.get("password"))
            path.is_visible = False
            path.save()
        elif path.is_password_protected is True:
            path.remove_password()
            url = path.get_url().replace("/", "_")
            session["has_entered_password_{url}"] = False
            path.save()

    return jsonify({"status": "success"})

@module_blueprint.route("/check-password/<path_id>", methods=["POST"])
def check_password(path_id):

    path = Path.query.get(path_id)

    password = request.form.get("password")

    print(".....", path.check_password(password), password, ">>><<<")
    if path.check_password(password) is True:
        url = path.get_url().replace("/", "_")
        session[f"has_entered_password_{url}"] = True
        return jsonify({"status": "success"})
    elif path.check_password(password) is False:
        url = path.get_url().replace("/", "_")
        session[f"has_entered_password_{url}"] = False
        return jsonify({"status": "error"})


@module_blueprint.route("/visibility/<path_id>", methods=["GET"])
@login_required
def toggle_visibility(path_id):
    path = Path.query.get(path_id)
    if not path.can_edit(current_user):
        flash("Insufficient permission", "warning")
        return redirect(url_for("www.index"))
    if path.is_visible == True:
        path.is_visible = False
    elif path.is_visible == False:
        path.is_visible = True
    path.update()
    if "next" in request.args:
        if request.args.get("next") != "":
            return redirect(get_safe_redirect(request.args.get("next")))
        else:
            return redirect(url_for("www.index"))
    else:
        return redirect(url_for("www.index"))


@module_blueprint.route("/set-visibility", methods=["POST"])
@login_required
def set_visibility():
    data = request.get_json(silent=True) or {}
    path = Path.query.get(data.get("path_id"))
    if not path:
        return jsonify({"success": False, "error": "Path not found"})
    if not path.can_edit(current_user):
        return jsonify({"success": False, "error": "Insufficient permission"})
    path.is_visible = bool(data.get("visible"))
    path.update()
    return jsonify({"success": True, "is_visible": path.is_visible})


@module_blueprint.route("/set-preview-policy", methods=["POST"])
@login_required
def set_preview_policy():
    data = request.get_json(silent=True) or {}
    path = Path.query.get(data.get("path_id"))
    if not path:
        return jsonify({"success": False, "error": "Path not found"})
    if not current_user.is_enterprise() or current_user != path.path_user:
        return jsonify(
            {"success": False, "error": "Enterprise path owners only"}
        )
    path.disable_previews = bool(data.get("disable"))
    path.update()
    return jsonify(
        {"success": True, "disable_previews": path.disable_previews}
    )


@module_blueprint.route("/settings", methods=["GET"])
@login_required
def settings():
    context = {}
    password_form = ChangePasswordForm()
    name_form = ChangeNameForm()
    emoji_classes = Emoji.query.all()
    context.update(
        {
            "password_form": password_form,
            "name_form": name_form,
            "emoji_classes": emoji_classes,
        }
    )
    return render_template(
        "linkolearn_theme/templates/profile_settings.html", **context
    )


@module_blueprint.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if not form.validate_on_submit():
        flash_errors(form)

    if not form.password1.data == form.password2.data:
        flash(notify("Passwords must be same", alert_type="success"))
        return mhelp.redirect_url(mhelp.info["module_name"] + ".settings")

    current_user.password = form.password1.data
    current_user.save()
    return mhelp.redirect_url(mhelp.info["module_name"] + ".settings")


@module_blueprint.route("/settings/name", methods=["POST"])
@login_required
def change_name():
    form = ChangeNameForm()
    if not form.validate_on_submit():
        flash_errors(form)
        return mhelp.redirect_url(mhelp.info["module_name"] + ".settings")
    current_user.first_name = form.first_name.data
    current_user.last_name = form.last_name.data
    current_user.save()
    return mhelp.redirect_url(mhelp.info["module_name"] + ".settings")


@module_blueprint.route("/settings/emoji", methods=["POST"])
@login_required
def change_emoji():
    emoji_classes = [_.class_name for _ in Emoji.query.all()]
    target_class = request.form["emoji_class"].strip()
    if not target_class in emoji_classes:
        flash(notify("Emoji class not found", alert_type="warning"))
        return mhelp.redirect_url(mhelp.info["module_name"] + ".settings")
    current_user.emoji_class = target_class
    current_user.save()
    return mhelp.redirect_url(mhelp.info["module_name"] + ".settings")


def sectionlinks2str(section_links):
    return "&#10;".join([_.url for _ in section_links])


@module_blueprint.route("/settings/p/<path_id>/delete", methods=["GET", "POST"])
@login_required
def delete_path(path_id):
    path = Path.query.get(path_id)
    if not path.path_user == current_user:
        return jsonify({"error": "x"})

    bm = BookmarkList.query.filter(BookmarkList.path_id == path_id).all()
    for b in bm:
        b.delete(commit=False)

    lm = LikeList.query.filter(LikeList.path_id == path_id).all()
    for l in lm:
        l.delete(commit=False)
    path.delete(commit=False)
    db.session.commit()
    return mhelp.redirect_url("www.user_profile", username=current_user.username)


@module_blueprint.route("/settings/p/<path_id>/edit", methods=["GET", "POST"])
@login_required
def edit_path(path_id):
    path = Path.query.get(path_id)
    if not path or not path.can_edit(current_user):
        flash("Insufficient permission", "warning")
        return redirect(path.get_url() if path else url_for("www.index"))

    if request.method == "GET":
        context = {}

        context.update(
            {"path": path, "sectionlinks2str": sectionlinks2str, "PATH_ICONS": PATH_ICONS}
        )
        return render_template("linkolearn_theme/templates/edit.html", **context)
    if request.method == "POST":
        json_submit = request.get_json()
        # path_title = json_submit['path_title']
        path_link = json_submit["path_link"]
        path_link = Path.slugify(path_link)
        sections = json_submit["sections"]
        path.sections = []
        # path.title = path_title
        path.slug = path_link
        # cover icon: whitelist only, never a raw client string (it is echoed
        # into a `fas {{icon}}` class attribute on the landing cards)
        path_icon = (json_submit.get("path_icon") or "").strip()
        path.cover_icon = path_icon if path_icon in PATH_ICON_CLASSES else ""

        for sec in sections:
            section = Section()
            sec_title = sec["section_title"]
            section.title = sec_title
            sec_links = sec["section_links"]
            print(sec_links)
            if sec_links.strip() != "":
                urls_ = sec_links.split("\n")
                urls = []
                for u in urls_:
                    if u.startswith("["):
                        if path.is_valid_markdown_link(u):
                            urls.append(u)
                    elif validators.url(u):
                        urls.append(u)
                    else:
                        pass
                section.links = list((Link(url=url) for url in urls))

            path.sections.append(section)
        path.save()

        next_url = path.get_url()
        return jsonify({"goto": next_url})


@module_blueprint.route("/bookmarks", methods=["GET", "POST"])
@login_required
def bookmarks():
    return render_template("linkolearn_theme/templates/bookmarks.html")


@module_blueprint.route("/api/paths", methods=["GET", "POST"])
@login_required
def get_paths():
    user = current_user
    paths = user.paths
    return jsonify([{"id": path.id, "title": path.slug} for path in paths])


@module_blueprint.route("/api/paths/<int:path_id>/sections", methods=["GET"])
@login_required
def get_sections(path_id):
    sections = Section.query.filter_by(path_id=path_id).all()
    return jsonify([{"id": section.id, "title": section.title} for section in sections])


@module_blueprint.route("/add-editor/", methods=["POST"])
@login_required
def add_editor():
    if current_user.subscription_plan is None:
        current_user.subscription_plan = 0

    if current_user.subscription_plan < 1:
        flash("You must be premium to add editors")
        return redirect(path.get_url())

    username = request.form.get("username")
    path_id = request.form.get("path_id")

    path = Path.query.get(path_id)

    editor = User.query.filter_by(username=username).first()
    if not editor:
        flash("User not found", "error")
        return redirect(path.get_url())

    if not (current_user == path.path_user):
        flash("No permission", "error")
        return redirect(path.get_url())

    path.add_editor(editor)
    db.session.commit()

    flash(f"Added {username} successfully", "success")
    return redirect(path.get_url())


@module_blueprint.route("/remove-editor/<username>/<path_id>/", methods=["GET"])
@login_required
def remove_editor(username, path_id):
    path = Path.query.get(path_id)

    if current_user.subscription_plan is None:
        current_user.subscription_plan = 0

    if current_user.subscription_plan < 1:
        flash("You must be premium to add editors")
        return redirect(path.get_url() if path else url_for("www.index"))

    path = Path.query.get(path_id)

    editor = User.query.filter_by(username=username).first()
    if not editor:
        flash("User not found", "error")
        return redirect(path.get_url())

    if not (current_user == path.path_user):
        flash("No permission", "error")
        return redirect(path.get_url())

    path.remove_editor(editor)
    db.session.commit()

    flash(f"Removed {username} successfully", "success")
    return redirect(path.get_url())


@module_blueprint.route("/add-link", methods=["POST"])
@login_required
def add_link():
    """Add a link to a section from the path page (inline 'Add link' form).

    Accepts a plain URL or the markdown form [Title](url), mirroring the
    edit-page convention.
    """
    section = Section.query.get(request.form.get("section_id"))
    raw = (request.form.get("url") or "").strip()

    if not section or not raw:
        return jsonify({"success": False, "error": "Invalid data"})

    path = section.section_path
    if not path.can_edit(current_user):
        return jsonify({"success": False, "error": "Permission denied"})

    url, title = raw, None
    if path.is_valid_markdown_link(raw):
        extracted = path.extract_link(raw)
        if extracted.get("href"):
            url, title = extracted["href"], extracted.get("text")

    if not validators.url(url):
        return jsonify({"success": False, "error": "That doesn't look like a valid URL."})

    link = Link(url=url, title=title, section_id=section.id)
    db.session.add(link)
    db.session.commit()

    return jsonify({"success": True})


@module_blueprint.route("/move_link", methods=["POST"])
@login_required
def move_link():
    link_id = request.form.get("link_id")
    from_section_id = request.form.get("from_section_id")
    section_id = request.form.get("section_id")

    link = Link.query.get(link_id)
    from_section = Section.query.get(from_section_id)
    to_section = Section.query.get(section_id)

    if not link or not from_section or not to_section:
        return jsonify({"success": False, "error": "Invalid data"})

    path = to_section.section_path
    if not path.can_edit(current_user):
        return jsonify({"success": False, "error": "Permission denied"})

    link.section_id = to_section.id
    db.session.commit()

    return jsonify({"success": True})


@module_blueprint.route("/generate_preview", methods=["POST"])
@login_required
def generate_preview():
    if not current_user.is_pro():
        return jsonify({"success": False, "error": "Pro subscription required"})

    data = request.get_json()
    link_id = data.get("link_id")
    link = Link.query.get(link_id)

    if not link:
        return jsonify({"success": False, "error": "Link not found"})

    if link.link_section.section_path.disable_previews:
        return jsonify(
            {"success": False,
             "error": "Link previews are disabled on this path"}
        )

    try:
        import requests
        from bs4 import BeautifulSoup

        url_to_scrape = link.url
        if link.url.startswith("["):
            path = link.link_section.section_path
            extracted_data = path.extract_link(link.url)
            url_to_scrape = extracted_data.get("href")

        if not url_to_scrape:
            return jsonify({"success": False, "error": "Invalid URL in markdown link"})

        response = requests.get(url_to_scrape)
        soup = BeautifulSoup(response.content, "html.parser")

        title = soup.find("title").string if soup.find("title") else ""
        description = soup.find("meta", attrs={"name": "description"})
        image = soup.find("meta", attrs={"property": "og:image"})

        link.title = title
        if description:
            link.description = description.get("content")
        if image:
            link.image_url = image.get("content")

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@module_blueprint.route("/remove_preview", methods=["POST"])
@login_required
def remove_preview():
    data = request.get_json()
    link_id = data.get("link_id")
    link = Link.query.get(link_id)

    if not link:
        return jsonify({"success": False, "error": "Link not found"})

    path = link.link_section.section_path
    if not (current_user == path.path_user or current_user in path.editors):
        return jsonify({"success": False, "error": "Permission denied"})

    link.title = None
    link.description = None
    link.image_url = None

    db.session.commit()
    return jsonify({"success": True})


@module_blueprint.route("/remove-all-previews", methods=["POST"])
@login_required
def remove_all_previews():
    data = request.get_json(silent=True) or {}
    path = Path.query.get(data.get("path_id"))
    if not path:
        return jsonify({"success": False, "error": "Path not found"})
    if not (current_user == path.path_user or current_user in path.editors):
        return jsonify({"success": False, "error": "Permission denied"})

    links = Link.query.join(Section).filter(Section.path_id == path.id).all()
    cleared = 0
    for link in links:
        if link.title or link.description or link.image_url:
            link.title = None
            link.description = None
            link.image_url = None
            cleared += 1
    db.session.commit()
    return jsonify({"success": True, "cleared": cleared})


@module_blueprint.route("/track-click", methods=["POST"])
def track_click():
    """Record a click on an org path link for the org's analytics.

    Called from the path page via keepalive fetch, so no login (public
    visitors click too). Only org paths are tracked.
    """
    data = request.get_json(silent=True) or {}
    link = Link.query.get(data.get("link_id"))
    if not link or not link.link_section:
        return jsonify({"success": False})
    path = link.link_section.section_path
    if not path or not path.team_id:
        return jsonify({"success": False, "error": "Not an organization path"})

    ua = request.user_agent.string or ""
    ua_l = ua.lower()
    if "tablet" in ua_l or "ipad" in ua_l:
        device = "Tablet"
    elif "mobile" in ua_l:
        device = "Mobile"
    else:
        device = "Desktop"

    EnterpriseAnalytics.track_click(
        team_id=path.team_id,
        link_id=link.id,
        referrer=(request.referrer or None),
        user_agent=ua[:500] or None,
        device_type=device,
    )
    return jsonify({"success": True})


ALLOWED_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def user_organizations(user):
    """Orgs the user owns or is a member of, owned ones first."""
    owned = (
        EnterpriseTeam.query.filter_by(owner_id=user.id)
        .order_by(EnterpriseTeam.created_at)
        .all()
    )
    member_ids = [
        m.team_id
        for m in EnterpriseTeamMember.query.filter_by(user_id=user.id).all()
    ]
    member_of = []
    if member_ids:
        member_of = (
            EnterpriseTeam.query.filter(
                EnterpriseTeam.id.in_(member_ids),
                EnterpriseTeam.owner_id != user.id,
            )
            .order_by(EnterpriseTeam.created_at)
            .all()
        )
    return owned + member_of


def _authorized_org(team_id=None):
    """Org a management action applies to: owner or member with admin role."""
    team_id = team_id or current_user.team_id
    if not team_id:
        return None
    team = EnterpriseTeam.query.get(team_id)
    if not team:
        return None
    if team.owner_id == current_user.id:
        return team
    member = EnterpriseTeamMember.query.filter_by(
        team_id=team.id, user_id=current_user.id
    ).first()
    if member and member.role == "admin":
        return team
    return None


def _save_org_logo(file, team_id):
    """Persist an uploaded org logo under static/uploads, return its URL."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_LOGO_EXTS:
        raise ValueError("Logo must be a PNG, JPG, GIF, WebP or SVG image")
    file.stream.seek(0, os.SEEK_END)
    if file.stream.tell() > 2 * 1024 * 1024:
        raise ValueError("Logo must be smaller than 2 MB")
    file.stream.seek(0)
    base_dir = current_app.config.get("BASE_DIR")
    rel_dir = os.path.join("static", "uploads", "org_logos")
    os.makedirs(os.path.join(base_dir, rel_dir), exist_ok=True)
    name = f"org_{team_id}_{uuid.uuid4().hex[:8]}{ext}"
    file.save(os.path.join(base_dir, rel_dir, name))
    return f"/static/uploads/org_logos/{name}"


def _unique_org_slug(name):
    base = Path.slugify(name) or "org"
    used = {
        row[0]
        for row in db.session.query(EnterpriseTeam.slug)
        .filter(EnterpriseTeam.slug.isnot(None))
        .all()
    }
    slug, n = base, 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    return slug


@module_blueprint.route("/enterprise/", methods=["GET"])
@login_required
def enterprise_dashboard():
    if not current_user.is_enterprise():
        flash("Enterprise plan required", "error")
        return redirect(url_for("linkolearn.dashboard"))

    orgs = user_organizations(current_user)
    # orgs the viewer may open the settings page for (owner or admin member)
    manageable = {o.id for o in orgs if _authorized_org(o.id)}

    return render_template(
        "linkolearn_theme/templates/enterprise.html",
        orgs=orgs,
        manageable=manageable,
    )


@module_blueprint.route("/enterprise/create-team/", methods=["POST"])
@login_required
def create_enterprise_team():
    if not current_user.is_enterprise():
        return jsonify({"success": False, "error": "Enterprise plan required"})

    team_name = (request.form.get("team_name") or "").strip()
    if not team_name:
        return jsonify({"success": False, "error": "Organization name required"})

    team = EnterpriseTeam(
        name=team_name,
        slug=_unique_org_slug(team_name),
        owner_id=current_user.id,
    )
    team.save()

    logo = request.files.get("logo")
    if logo and logo.filename:
        try:
            team.logo_url = _save_org_logo(logo, team.id)
            team.save()
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)})

    # keep the legacy pointer: the first org becomes the default team
    if not current_user.team_id:
        current_user.team_id = team.id
        current_user.save()

    return jsonify({"success": True, "team_id": team.id})


@module_blueprint.route("/enterprise/update-logo/", methods=["POST"])
@login_required
def update_enterprise_logo():
    team = EnterpriseTeam.query.get(request.form.get("team_id", type=int))
    if not team:
        return jsonify({"success": False, "error": "Organization not found"})
    if team.owner_id != current_user.id:
        return jsonify(
            {"success": False,
             "error": "Only the organization owner can change the logo"}
        )
    logo = request.files.get("logo")
    if not logo or not logo.filename:
        return jsonify({"success": False, "error": "Choose an image first"})
    try:
        team.logo_url = _save_org_logo(logo, team.id)
        team.save()
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": True, "logo_url": team.logo_url})


@module_blueprint.route("/enterprise/add-member/", methods=["POST"])
@login_required
def add_enterprise_member():
    team = _authorized_org(request.form.get("team_id", type=int))
    if not team:
        return jsonify({"success": False, "error": "Not allowed for this organization"})

    username = request.form.get("username")
    role = request.form.get("role", "member")

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"})

    existing = EnterpriseTeamMember.query.filter_by(
        team_id=team.id, user_id=user.id
    ).first()
    if existing:
        return jsonify({"success": False, "error": "User already in team"})

    member = EnterpriseTeamMember.add_member(team.id, user.id, role)

    if not user.team_id:
        user.team_id = team.id
    db.session.commit()

    EnterpriseAuditLog.log_action(
        team_id=team.id,
        user_id=current_user.id,
        action="member_added",
        details=f"Added {username} as {role}",
    )

    return jsonify({"success": True})


@module_blueprint.route("/enterprise/remove-member/<int:member_id>/", methods=["POST"])
@login_required
def remove_enterprise_member(member_id):
    member = EnterpriseTeamMember.query.get(member_id)
    if not member:
        return jsonify({"success": False, "error": "Member not found"})
    if not _authorized_org(member.team_id):
        return jsonify({"success": False, "error": "Not allowed for this organization"})

    user = User.query.get(member.user_id)
    if user and user.team_id == member.team_id:
        user.team_id = None

    db.session.delete(member)
    db.session.commit()

    return jsonify({"success": True})


@module_blueprint.route("/enterprise/add-domain/", methods=["POST"])
@login_required
def add_enterprise_domain():
    team = _authorized_org(request.form.get("team_id", type=int))
    if not team:
        return jsonify({"success": False, "error": "Not allowed for this organization"})

    domain = request.form.get("domain")
    if not domain:
        return jsonify({"success": False, "error": "Domain required"})

    existing = EnterpriseCustomDomain.query.filter_by(domain=domain).first()
    if existing:
        return jsonify({"success": False, "error": "Domain already in use"})

    custom_domain = EnterpriseCustomDomain.add_domain(team.id, domain)

    EnterpriseAuditLog.log_action(
        team_id=team.id,
        user_id=current_user.id,
        action="domain_added",
        details=f"Added domain {domain}",
    )

    return jsonify({"success": True})


@module_blueprint.route("/enterprise/remove-domain/<int:domain_id>/", methods=["POST"])
@login_required
def remove_enterprise_domain(domain_id):
    domain = EnterpriseCustomDomain.query.get(domain_id)
    if not domain or not _authorized_org(domain.team_id):
        return jsonify({"success": False, "error": "Domain not found"})

    db.session.delete(domain)
    db.session.commit()

    return jsonify({"success": True})
