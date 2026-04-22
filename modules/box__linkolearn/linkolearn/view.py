from shopyo.api.module import ModuleHelp
from flask import render_template
from flask import url_for
from flask import redirect
from flask import flash
from flask import request
from flask import jsonify
from flask import session

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
    if not (path.path_user == current_user):
        if not (current_user in path.editors):
            flash("Insufficient permission", "warning")
            return redirect(path.get_url())

    if request.method == "GET":
        context = {}

        context.update({"path": path, "sectionlinks2str": sectionlinks2str})
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
    if current_user.subscription_plan is None:
        current_user.subscription_plan = 0

    if current_user.subscription_plan < 1:
        flash("You must be premium to add editors")
        return redirect(path.get_url())

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
    if not (current_user == path.path_user or current_user in path.editors):
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


@module_blueprint.route("/enterprise/", methods=["GET"])
@login_required
def enterprise_dashboard():
    if not current_user.is_enterprise():
        flash("Enterprise plan required", "error")
        return redirect(url_for("linkolearn.dashboard"))

    team = None
    if current_user.team_id:
        team = EnterpriseTeam.query.get(current_user.team_id)

    members = []
    analytics = []
    domains = []

    if team:
        members = EnterpriseTeamMember.query.filter_by(team_id=team.id).all()
        for m in members:
            m.user = User.query.get(m.user_id)
        analytics = (
            EnterpriseAnalytics.query.filter_by(team_id=team.id)
            .order_by(EnterpriseAnalytics.event_date.desc())
            .limit(30)
            .all()
        )
        domains = EnterpriseCustomDomain.query.filter_by(team_id=team.id).all()
        team_paths = Path.query.filter_by(team_id=team.id).all()
        for p in team_paths:
            p.owner = User.query.get(p.user_id)

    return render_template(
        "linkolearn_theme/templates/enterprise.html",
        team=team,
        members=members,
        analytics=analytics,
        domains=domains,
        team_paths=team_paths,
    )


@module_blueprint.route("/enterprise/create-team/", methods=["POST"])
@login_required
def create_enterprise_team():
    if not current_user.is_enterprise():
        return jsonify({"success": False, "error": "Enterprise plan required"})

    if current_user.team_id:
        return jsonify({"success": False, "error": "Team already exists"})

    team_name = request.form.get("team_name")
    if not team_name:
        return jsonify({"success": False, "error": "Team name required"})

    team = current_user.create_enterprise_team(team_name)
    return jsonify({"success": True, "team_id": team.id})


@module_blueprint.route("/enterprise/add-member/", methods=["POST"])
@login_required
def add_enterprise_member():
    if not current_user.is_enterprise() or not current_user.team_id:
        return jsonify({"success": False, "error": "Enterprise plan required"})

    username = request.form.get("username")
    role = request.form.get("role", "member")

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"})

    existing = EnterpriseTeamMember.query.filter_by(
        team_id=current_user.team_id, user_id=user.id
    ).first()
    if existing:
        return jsonify({"success": False, "error": "User already in team"})

    member = EnterpriseTeamMember.add_member(current_user.team_id, user.id, role)

    user.team_id = current_user.team_id
    db.session.commit()

    EnterpriseAuditLog.log_action(
        team_id=current_user.team_id,
        user_id=current_user.id,
        action="member_added",
        details=f"Added {username} as {role}",
    )

    return jsonify({"success": True})


@module_blueprint.route("/enterprise/remove-member/<int:member_id>/", methods=["POST"])
@login_required
def remove_enterprise_member(member_id):
    if not current_user.is_enterprise() or not current_user.team_id:
        return jsonify({"success": False, "error": "Enterprise plan required"})

    member = EnterpriseTeamMember.query.get(member_id)
    if not member or member.team_id != current_user.team_id:
        return jsonify({"success": False, "error": "Member not found"})

    user = User.query.get(member.user_id)
    if user:
        user.team_id = None

    db.session.delete(member)
    db.session.commit()

    return jsonify({"success": True})


@module_blueprint.route("/enterprise/add-domain/", methods=["POST"])
@login_required
def add_enterprise_domain():
    if not current_user.is_enterprise() or not current_user.team_id:
        return jsonify({"success": False, "error": "Enterprise plan required"})

    domain = request.form.get("domain")
    if not domain:
        return jsonify({"success": False, "error": "Domain required"})

    existing = EnterpriseCustomDomain.query.filter_by(domain=domain).first()
    if existing:
        return jsonify({"success": False, "error": "Domain already in use"})

    custom_domain = EnterpriseCustomDomain.add_domain(current_user.team_id, domain)

    EnterpriseAuditLog.log_action(
        team_id=current_user.team_id,
        user_id=current_user.id,
        action="domain_added",
        details=f"Added domain {domain}",
    )

    return jsonify({"success": True})


@module_blueprint.route("/add-link-to-section/", methods=["POST"])
@login_required
def add_link_to_section():
    data = request.get_json()
    section_id = data.get("section_id")
    url = data.get("url")

    if not section_id or not url:
        return jsonify({"success": False, "error": "Missing section_id or url"})

    section = Section.query.get(section_id)
    if not section:
        return jsonify({"success": False, "error": "Section not found"})

    path = section.section_path
    if not path.can_edit(current_user):
        return jsonify({"success": False, "error": "Permission denied"})

    link = Link(url=url)
    section.links.append(link)
    db.session.commit()

    return jsonify({"success": True})


@module_blueprint.route("/enterprise/remove-domain/<int:domain_id>/", methods=["POST"])
@login_required
def remove_enterprise_domain(domain_id):
    if not current_user.is_enterprise() or not current_user.team_id:
        return jsonify({"success": False, "error": "Enterprise plan required"})

    domain = EnterpriseCustomDomain.query.get(domain_id)
    if not domain or domain.team_id != current_user.team_id:
        return jsonify({"success": False, "error": "Domain not found"})

    db.session.delete(domain)
    db.session.commit()

    return jsonify({"success": True})
