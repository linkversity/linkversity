import os
import json
import datetime
from app import app

from modules.box__default.auth.models import User
from init import db

from modules.box__linkolearn.linkolearn.models import Path
from modules.box__linkolearn.linkolearn.models import Section
from modules.box__linkolearn.linkolearn.models import Link
from modules.box__linkolearn.linkolearn.models import LikeList
from modules.box__linkolearn.linkolearn.models import BookmarkList
from modules.box__linkolearn.linkolearn.models import Emoji

dirpath = os.path.dirname(os.path.abspath(__file__))

json_path = os.path.join(dirpath, 'data', 'default_courses.json')
with open(json_path) as f:
    userdata = json.load(f)


data = userdata['osdotsystem']

def upload_default_users():
    with app.app_context():
        user = User()
        user.email = 'arj.python@gmail.com'
        user.password = 'pass1234'
        user.is_admin = True
        user.is_email_confirmed = True
        user.username = 'osdotsystem'
        user.email_confirm_date = datetime.datetime.now()
        user.like_list = LikeList()
        user.bookmark_list = BookmarkList()

        path = Path(
            title=data['title'],
            slug=data['slug'],
            )
        for section in data['sections']:
            section = Section(
                title = section['title']
                )
            for url in section['links']:
                link = Link(url=url)
                section.links.append(link)
            path.sections.append(section)
        user.paths.append(path)
        user.save()


def upload_emoji_css():
    emoji_css_path = os.path.join(dirpath, 'data', 'emoji.txt')
    with open(emoji_css_path) as f:
        emoji_classes = [_ for _ in f.read().split() if _.strip()]

    with app.app_context():
        for class_name in emoji_classes:
            e = Emoji()
            e.class_name = class_name
            e.save(commit=False)

        db.session.commit()


def upload():
    print('Uploading paths')
    upload_default_users()