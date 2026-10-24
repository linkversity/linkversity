import os
from datetime import datetime

from shopyo.api.module import ModuleHelp

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]


from flask import render_template
from flask import abort
from flask import request
from flask import url_for
from flask import Response

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


@module_blueprint.route("/feed.xml")
def feed():
    """RSS 2.0 feed of all posts."""
    from email.utils import format_datetime
    from xml.sax.saxutils import escape

    base = request.host_url.rstrip("/")
    posts = get_all_posts()

    items = []
    for p in posts:
        link = f"{base}{url_for('blog.post', slug=p['slug'])}"
        pub = ""
        if p.get("date"):
            try:
                dt = datetime.strptime(p["date"], "%Y-%m-%d")
                pub = f"<pubDate>{format_datetime(dt)}</pubDate>"
            except ValueError:
                pass
        items.append(
            "<item>"
            f"<title>{escape(p['title'])}</title>"
            f"<link>{escape(link)}</link>"
            f"<guid isPermaLink=\"true\">{escape(link)}</guid>"
            f"<description>{escape(p.get('description') or '')}</description>"
            f"{pub}"
            "</item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "<channel>\n"
        "<title>Linkversity Blog</title>\n"
        f"<link>{escape(base + url_for('blog.index'))}</link>\n"
        "<description>Notes on learning systems, curation, and teaching with links.</description>\n"
        + "\n".join(items)
        + "\n</channel>\n"
        "</rss>\n"
    )
    return Response(xml, mimetype="application/rss+xml")
