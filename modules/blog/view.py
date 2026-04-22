import os

from shopyo.api.module import ModuleHelp

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]


from flask import render_template
from flask import abort

from modules.blog.models import get_all_posts
from modules.blog.models import get_post_by_slug


@module_blueprint.route("/")
def index():
    posts = get_all_posts()
    return render_template("blog/index.html", posts=posts)


@module_blueprint.route("/<slug>")
def post(slug):
    post = get_post_by_slug(slug)
    if not post:
        abort(404)
    return render_template("blog/post.html", post=post)
