import json
import os

from flask import url_for
from flask import redirect
from flask import flash
# from flask import request
from flask import Blueprint
from flask import render_template

#
from shopyo.api.html import notify
# from shopyo.api.forms import flash_errors
# from shopyo.api.enhance import get_active_theme_dir
# from shopyo.api.enhance import get_setting

# from modules.box__ecommerce.shop.helpers import get_cart_data

from flask_login import current_user
from sqlalchemy import func

from modules.box__linkolearn.linkolearn.models import Path
from modules.box__default.auth.models import User

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
        paths = Path.query.all()
        paths = [p for p in paths if p.is_visible]
        if len(paths) >= 5:
            return paths[-6:-1]
        else:
            len_paths = len(paths) +1
            return paths[:len_paths]

    context = {
        'get_last_5': get_last_5
    }

    return render_template("linkolearn_theme/index.html", **context)


@module_blueprint.route("/<username>")
def user_profile(username):
    context = {}
    user = User.query.filter(
        func.lower(User.username) == func.lower(username)
        ).first_or_404()
    context.update({'user': user})
    return render_template("linkolearn_theme/templates/profile.html", **context)


@module_blueprint.route("/<username>/<path_slug>")
def path(username, path_slug):
    user = User.query.filter(User.username == username).first_or_404()
    path = Path.query.filter(Path.slug == path_slug, Path.user_id == user.id).first_or_404()
    if (not path.is_visible):
        if (current_user.is_authenticated):
            if(path.path_user == current_user):
                pass
            else:
                flash(notify("Path not public!", alert_type='warning'))
                return redirect(url_for('www.index'))
        else:
            flash(notify("Path not public!", alert_type='warning'))
            return redirect(url_for('www.index'))

    context = {}
    user = User.query.filter(
        func.lower(User.username) == func.lower(username)
        ).first_or_404()
    
    context.update({'user': user, 'path': path})
    return render_template("linkolearn_theme/templates/path.html", **context)


@module_blueprint.route("/privacy-policy")
def privacy_policy():
    return render_template("linkolearn_theme/templates/info/privacy_policy.html")


@module_blueprint.route("/contact")
def contact():
    return render_template("linkolearn_theme/templates/info/contact.html")

@module_blueprint.route("/about")
def about():
    return render_template("linkolearn_theme/templates/info/about.html")