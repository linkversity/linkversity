
from shopyo.api.module import ModuleHelp
from flask import render_template
from flask import url_for
# from flask import redirect
# from flask import flash
from flask import request
from flask import jsonify

import validators

# from shopyo.api.html import notify_success
# from shopyo.api.forms import flash_errors

from flask_login import login_required
from flask_login import current_user

from modules.box__linkolearn.linkolearn.models import Path
from modules.box__linkolearn.linkolearn.models import Section
from modules.box__linkolearn.linkolearn.models import Link
from modules.box__linkolearn.linkolearn.models import BookmarkList
from modules.box__linkolearn.linkolearn.models import LikeList

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]


@module_blueprint.route("/")
@login_required
def index():
    return render_template('linkolearn_theme/templates/new.html')


@module_blueprint.route("/add", methods=['POST'])
@login_required
def add():
    json_submit = request.get_json()
    # path_title = json_submit['path_title']
    path_link = json_submit['path_link']
    sections = json_submit['sections']

    if not path_link.strip():
        return jsonify({'errmsg': "Slug should not be empty"})
    
    exists = Path.query.filter(Path.slug == path_link).first()
    if exists:
        return jsonify({'errmsg': "Path exists"})
    path = Path()
    path.like_list = LikeList()
    path.bookmark_list = BookmarkList()
    path.title = ""
    path.slug = path_link

    for sec in sections:
        section = Section()
        sec_title = sec['section_title']
        section.title = sec_title
        sec_links = sec['section_links']
        if sec_links.strip() != '' and '\n' in sec_links:
            urls = sec_links.split('\n')
            urls = list((url for url in urls if validators.url(url)))
            section.links = list((Link(url=url) for url in urls))
        path.sections.append(section)
    path.path_user = current_user
    path.save()

    next_url = url_for('www.path', username=current_user.username, path_slug=path.slug)
    # next_url = f"{current_user.username}/{path.slug}"
    return jsonify({'goto': next_url})
