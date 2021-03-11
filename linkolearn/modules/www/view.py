import json
import os

# from flask import url_for
# from flask import redirect
# from flask import flash
# from flask import request
from flask import Blueprint
from flask import render_template

#
# from shopyo.api.html import notify_success
# from shopyo.api.forms import flash_errors
# from shopyo.api.enhance import get_active_theme_dir
# from shopyo.api.enhance import get_setting

# from modules.box__ecommerce.shop.helpers import get_cart_data


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

    return render_template("linkolearn_theme/index.html")


@module_blueprint.route("/<username>")
def user_profile(username):
    context = {}
    user = User.query.filter(User.username == username).first_or_404()
    context.update({'user': user})
    return render_template("linkolearn_theme/templates/profile.html", **context)


@module_blueprint.route("/<username>/<path_slug>")
def path(username, path_slug):
    context = {}
    user = User.query.filter(User.username == username).first_or_404()
    path = Path.query.filter(Path.slug == path_slug).first_or_404()
    context.update({'user': user, 'path': path})
    return render_template("linkolearn_theme/templates/path.html", **context)