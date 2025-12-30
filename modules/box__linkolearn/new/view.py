
from shopyo.api.module import ModuleHelp
from flask import render_template
from flask import url_for
# from flask import redirect
# from flask import flash
from flask import request
from flask import jsonify

import validators
from urlextract import URLExtract

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
    path_link = Path.slugify(path_link)
    sections = json_submit['sections']

    if not path_link.strip():
        return jsonify({'errmsg': "Slug should not be empty"})
    
    exists = Path.query.filter(Path.slug == path_link, Path.user_id == current_user.id).first()
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

        if (sec_links.strip() != ''):
            urls_ = sec_links.split('\n')

            urls = []

            for u in urls_:
                if u.startswith('['):
                    if path.is_valid_markdown_link(u):
                        urls.append(u)
                elif validators.url(u):
                    urls.append(u)
                else:
                    pass
            section.links = list((Link(url=url) for url in urls))
        path.sections.append(section)
    path.path_user = current_user
    path.save()

    next_url = url_for('www.path', username=current_user.username, path_slug=path.slug)
    # next_url = f"{current_user.username}/{path.slug}"
    return jsonify({'goto': next_url})


@module_blueprint.route("/upload", methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        if 'document' not in request.files:
            return jsonify({'errmsg': 'No document part'})
        
        file = request.files['document']
        if file.filename == '':
            return jsonify({'errmsg': 'No selected document'})
        
        if file:
            # Assuming the document is text-based for now
            # For more complex documents (PDF, DOCX), dedicated parsers would be needed
            try:
                document_content = file.read().decode('utf-8')
            except UnicodeDecodeError:
                return jsonify({'errmsg': 'Failed to decode file. Please upload a UTF-8 encoded text, HTML, or Markdown file.'})
            
            extractor = URLExtract()
            urls = extractor.find_urls(document_content, only_unique=True)

            path_title = request.form.get('path_title')
            if not path_title or not path_title.strip():
                path_title = 'Uploaded Document Path'
            
            path_slug = Path.slugify(path_title)
            
            # Check for existing path with the same slug for the current user
            exists = Path.query.filter(Path.slug == path_slug, Path.user_id == current_user.id).first()
            if exists:
                import random
                import string
                random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                path_slug = f"{path_slug}-{random_str}"
            
            new_path = Path()
            new_path.like_list = LikeList()
            new_path.bookmark_list = BookmarkList()
            new_path.title = path_title
            new_path.slug = path_slug
            new_path.path_user = current_user

            if urls:
                section = Section(title="Links from Uploaded Document")
                valid_urls_found = False
                for url_str in urls:
                    # extractor might return things that are not exactly full urls with scheme
                    # validators.url handles this
                    if url_str.startswith('http'):
                        if validators.url(url_str):
                            link = Link(url=url_str)
                            section.links.append(link)
                            valid_urls_found = True
                    else:
                        # try adding http
                        if validators.url('http://' + url_str):
                            link = Link(url='http://' + url_str)
                            section.links.append(link)
                            valid_urls_found = True
                
                if not valid_urls_found:
                     return jsonify({'errmsg': 'No valid URLs found in the document.'})
                
                new_path.sections.append(section)
            else:
                return jsonify({'errmsg': 'No links found in the document.'})

            new_path.save()
            
            next_url = url_for('www.path', username=current_user.username, path_slug=new_path.slug)
            return jsonify({'goto': next_url})
    
    return render_template('linkolearn_theme/templates/upload_document.html')
