import os
from datetime import datetime

from markdown_it import MarkdownIt


def get_post_fields(content):
    fields = {}
    lines = content.split("\n")
    in_frontmatter = False
    frontmatter_content = []
    body_lines = []
    in_body = False

    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                in_body = False
            else:
                in_frontmatter = False
                in_body = True
            continue
        if in_frontmatter:
            frontmatter_content.append(line)
        elif not in_body and not frontmatter_content:
            in_body = True

        if in_body:
            body_lines.append(line)

    for line in frontmatter_content:
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

    body = "\n".join(body_lines)
    return fields, body


def parse_markdown_post(filename):
    filepath = os.path.join(os.path.dirname(__file__), "posts", filename)
    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    fields, body = get_post_fields(content)

    md = MarkdownIt("commonmark", {"breaks": True, "html": True})
    html = md.render(body)

    slug = filename.replace(".md", "")

    title_raw = fields.get("title", slug.replace("-", " ").title())

    return {
        "slug": slug,
        "title": title_raw.strip('"').strip("'"),
        "description": fields.get("description", ""),
        "keywords": fields.get("keywords", ""),
        "date": fields.get("date", "").strip('"').strip("'"),
        "author": fields.get("author", ""),
        "content": html,
        "raw_content": body,
    }


def get_all_posts():
    posts_dir = os.path.join(os.path.dirname(__file__), "posts")
    if not os.path.exists(posts_dir):
        return []

    posts = []
    for filename in os.listdir(posts_dir):
        if filename.endswith(".md"):
            post = parse_markdown_post(filename)
            if post:
                posts.append(post)

    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts


def get_post_by_slug(slug):
    filename = f"{slug}.md"
    return parse_markdown_post(filename)
