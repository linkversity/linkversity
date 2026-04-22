from shopyo.api.module import ModuleHelp
from flask import render_template
from flask import url_for
from flask import redirect

# from flask import flash
from flask import request
from flask import jsonify

import validators
from urlextract import URLExtract
import requests
from bs4 import BeautifulSoup

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


def scrape_link_metadata(url):
    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            title = soup.find("title").text if soup.find("title") else ""

            description = ""
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            if desc_tag:
                description = desc_tag.get("content", "")

            image_url = ""
            img_tag = soup.find("meta", attrs={"property": "og:image"}) or soup.find(
                "meta", attrs={"name": "twitter:image"}
            )
            if img_tag:
                image_url = img_tag.get("content", "")

            return {
                "title": title.strip()[:500] if title else "",
                "description": description.strip() if description else "",
                "image_url": image_url.strip()[:500] if image_url else "",
            }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return None


@module_blueprint.route("/")
@login_required
def index():
    team_id = request.args.get("team_id")
    return render_template("linkolearn_theme/templates/new.html", team_id=team_id)


@module_blueprint.route("/add", methods=["POST"])
@login_required
def add():
    json_submit = request.get_json()
    # path_title = json_submit['path_title']
    path_link = json_submit["path_link"]
    path_link = Path.slugify(path_link)
    sections = json_submit["sections"]
    team_id = json_submit.get("team_id")

    if not path_link.strip():
        return jsonify({"errmsg": "Slug should not be empty"})

    if team_id:
        if not current_user.is_enterprise() or current_user.team_id != int(team_id):
            return jsonify({"errmsg": "Invalid team"})
        exists = Path.query.filter(
            Path.slug == path_link, Path.team_id == int(team_id)
        ).first()
    else:
        exists = Path.query.filter(
            Path.slug == path_link, Path.user_id == current_user.id
        ).first()
    if exists:
        return jsonify({"errmsg": "Path exists"})
    path = Path()
    path.like_list = LikeList()
    path.bookmark_list = BookmarkList()
    path.title = ""
    path.slug = path_link
    if team_id:
        path.team_id = int(team_id)

    is_pro = current_user.is_pro()

    for sec in sections:
        section = Section()
        sec_title = sec["section_title"]
        section.title = sec_title
        sec_links = sec["section_links"]

        if sec_links.strip() != "":
            urls_ = sec_links.split("\n")

            urls = []

            for u in urls_:
                u = u.strip()
                if not u:
                    continue

                final_url = None
                if u.startswith("["):
                    if path.is_valid_markdown_link(u):
                        final_url = u
                elif validators.url(u):
                    final_url = u
                elif validators.url("http://" + u):
                    final_url = "http://" + u

                if final_url:
                    link = Link(url=final_url)
                    if is_pro:
                        scrape_url = final_url
                        if final_url.startswith("["):
                            extract = path.extract_link(final_url)
                            scrape_url = extract.get("href")

                        if scrape_url:
                            metadata = scrape_link_metadata(scrape_url)
                            if metadata:
                                link.title = metadata["title"]
                                link.description = metadata["description"]
                                link.image_url = metadata["image_url"]
                    section.links.append(link)

        path.sections.append(section)
    path.path_user = current_user
    path.save()

    next_url = url_for("www.path", username=current_user.username, path_slug=path.slug)
    # next_url = f"{current_user.username}/{path.slug}"
    return jsonify({"goto": next_url})


@module_blueprint.route("/upload", methods=["GET", "POST"])
@login_required
def upload_document():
    if not current_user.is_pro():
        return redirect(url_for("www.activate"))

    if request.method == "POST":
        if "document" not in request.files:
            return jsonify({"errmsg": "No document part"})

        file = request.files["document"]
        if file.filename == "":
            return jsonify({"errmsg": "No selected document"})

        if file:
            # Assuming the document is text-based for now
            # For more complex documents (PDF, DOCX), dedicated parsers would be needed
            try:
                document_content = file.read().decode("utf-8")
            except UnicodeDecodeError:
                return jsonify(
                    {
                        "errmsg": "Failed to decode file. Please upload a UTF-8 encoded text, HTML, or Markdown file."
                    }
                )

            extractor = URLExtract()
            urls = extractor.find_urls(document_content, only_unique=True)

            is_pro = current_user.is_pro()
            disable_preview = request.form.get("disable_preview")

            if not urls:
                return jsonify({"errmsg": "No links found in the document."})

            # Check if updating an existing path
            existing_path_id = request.form.get("existing_path_id")
            path_to_save = None

            if existing_path_id and existing_path_id != "none":
                existing_path = Path.query.get(existing_path_id)
                if existing_path and existing_path.user_id == current_user.id:
                    path_to_save = existing_path
                else:
                    return jsonify({"errmsg": "Invalid path selected."})
            else:
                path_title = request.form.get("path_title")
                if not path_title or not path_title.strip():
                    path_title = "Uploaded Document Path"

                path_slug = Path.slugify(path_title)

                # Check for existing path with the same slug for the current user
                exists = Path.query.filter(
                    Path.slug == path_slug, Path.user_id == current_user.id
                ).first()
                if exists:
                    import random
                    import string

                    random_str = "".join(
                        random.choices(string.ascii_lowercase + string.digits, k=4)
                    )
                    path_slug = f"{path_slug}-{random_str}"

                new_path = Path()
                new_path.like_list = LikeList()
                new_path.bookmark_list = BookmarkList()
                new_path.title = path_title
                new_path.slug = path_slug
                new_path.path_user = current_user
                path_to_save = new_path

            section = Section(title="Links from Uploaded Document")
            valid_urls_found = False
            for url_str in urls:
                # extractor might return things that are not exactly full urls with scheme
                # validators.url handles this
                final_url = None
                if url_str.startswith("http"):
                    if validators.url(url_str):
                        final_url = url_str
                else:
                    # try adding http
                    if validators.url("http://" + url_str):
                        final_url = "http://" + url_str

                if final_url:
                    link = Link(url=final_url)
                    if is_pro and not disable_preview:
                        metadata = scrape_link_metadata(final_url)
                        if metadata:
                            link.title = metadata["title"]
                            link.description = metadata["description"]
                            link.image_url = metadata["image_url"]
                    section.links.append(link)
                    valid_urls_found = True

            if not valid_urls_found:
                return jsonify({"errmsg": "No valid URLs found in the document."})

            path_to_save.sections.append(section)
            path_to_save.save()

            next_url = url_for(
                "www.path", username=current_user.username, path_slug=path_to_save.slug
            )
            return jsonify({"goto": next_url})

    user_paths = Path.query.filter_by(user_id=current_user.id).all()
    selected_path_id = request.args.get("existing_path_id")
    return render_template(
        "linkolearn_theme/templates/upload_document.html",
        user_paths=user_paths,
        selected_path_id=selected_path_id,
    )
