
from shopyo.api.module import ModuleHelp
from flask import render_template
from flask import url_for
from flask import redirect
from flask import flash
from flask import request
from flask import jsonify

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
from modules.box__linkolearn.linkolearn.forms import ChangeNameForm
from modules.box__linkolearn.linkolearn.forms import ChangePasswordForm

from shopyo.api.security import get_safe_redirect
from shopyo.api.forms import flash_errors
from shopyo.api.html import notify

import validators

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]

@module_blueprint.route("/")
def index():
    return mhelp.info['display_string']


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
    if 'next' in request.args:
        if request.args.get('next') != '':
            return redirect(get_safe_redirect(request.args.get('next')))
        else:
            return redirect(url_for('www.index'))
    else:
        return redirect(url_for('www.index'))



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
    if 'next' in request.args:
        if request.args.get('next') != '':
            return redirect(get_safe_redirect(request.args.get('next')))
        else:
            return redirect(url_for('www.index'))
    else:
        return redirect(url_for('www.index'))


@module_blueprint.route("/visibility/<path_id>", methods=["GET"])
@login_required
def toggle_visibility(path_id):
    path = Path.query.get(path_id)
    if path.is_visible == True:
        path.is_visible = False
    elif path.is_visible == False:
        path.is_visible = True
    path.update()
    if 'next' in request.args:
        if request.args.get('next') != '':
            return redirect(get_safe_redirect(request.args.get('next')))
        else:
            return redirect(url_for('www.index'))
    else:
        return redirect(url_for('www.index'))


@module_blueprint.route("/settings", methods=["GET"])
@login_required
def settings():
    context = {}
    password_form = ChangePasswordForm()
    name_form = ChangeNameForm()
    emoji_classes = Emoji.query.all()
    context.update({
        'password_form': password_form,
        'name_form': name_form,
        'emoji_classes': emoji_classes
        })
    return render_template('linkolearn_theme/templates/profile_settings.html', **context)


@module_blueprint.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if not form.validate_on_submit():
        flash_errors(form)

    if not form.password1.data == form.password2.data:
        flash(notify('Passwords must be same', alert_type='success'))
        return mhelp.redirect_url(mhelp.info['module_name']+'.settings')

    current_user.password = form.password1.data
    current_user.save()
    return mhelp.redirect_url(mhelp.info['module_name']+'.settings')


@module_blueprint.route("/settings/name", methods=["POST"])
@login_required
def change_name():
    form = ChangeNameForm()
    if not form.validate_on_submit():
        flash_errors(form)
        return mhelp.redirect_url(mhelp.info['module_name']+'.settings')
    current_user.first_name = form.first_name.data
    current_user.last_name = form.last_name.data
    current_user.save()
    return mhelp.redirect_url(mhelp.info['module_name']+'.settings')



@module_blueprint.route("/settings/emoji", methods=["POST"])
@login_required
def change_emoji():
    emoji_classes = [_.class_name for _ in Emoji.query.all()]
    target_class = request.form['emoji_class'].strip()
    if not target_class in emoji_classes:
        flash(notify('Emoji class not found', alert_type='warning'))
        return mhelp.redirect_url(mhelp.info['module_name']+'.settings')
    current_user.emoji_class = target_class
    current_user.save()
    return mhelp.redirect_url(mhelp.info['module_name']+'.settings')

def sectionlinks2str(section_links):
    return '&#10;'.join([_.url for _ in section_links])


@module_blueprint.route("/settings/p/<path_id>/edit", methods=["GET", "POST"])
@login_required
def edit_path(path_id):
    path = Path.query.get(path_id)
    if not path.path_user == current_user:
        return jsonify({'error': 'x'})
    if request.method == 'GET':
        context = {}
        
        context.update({
            'path': path,
            'sectionlinks2str': sectionlinks2str
            })
        return render_template('linkolearn_theme/templates/edit.html', **context)
    if request.method == 'POST':
        json_submit = request.get_json()
        path_title = json_submit['path_title']
        path_link = json_submit['path_link']
        sections = json_submit['sections']
        path.sections = []
        path.title = path_title
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
        path.save()

        next_url = url_for('www.path', username=current_user.username, path_slug=path.slug)
        return jsonify({'goto': next_url})


@module_blueprint.route("/bookmarks", methods=["GET", "POST"])
@login_required
def bookmarks():
    return render_template('linkolearn_theme/templates/bookmarks.html')