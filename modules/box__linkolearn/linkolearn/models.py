import datetime

from flask import url_for

from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from shopyo.api.models import PkModel
from modules.box__default.auth.models import User
from init import db

import re
from markdown_it import MarkdownIt
from slugify import slugify as slugify_func


class Path(PkModel):
    __tablename__ = "paths"
    
    slug = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    sections = db.relationship("Section", backref="section_path", lazy=True, cascade="all, delete-orphan")

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)

    # Password for protection
    _password = db.Column(db.String(128), nullable=True)

    # Optional: Enforce password protection at creation
    is_password_protected = db.Column(db.Boolean, default=False)

    # Relationships
    like_list = db.relationship("LikeList", backref="like_list_path", lazy=True, uselist=False)
    bookmark_list = db.relationship("BookmarkList", backref="bookmark_list_path", lazy=True, uselist=False)

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, plaintext):
        self._password = generate_password_hash(plaintext, method="sha256")
        self.is_password_protected = True

    def check_password(self, password):
        if self._password is None:
            return False
        return check_password_hash(self._password, password)

    def remove_password(self):
        """Remove password protection from the path."""
        self._password = None
        self.is_password_protected = False

    def get_url(self):
        return url_for(
            "www.path", username=self.path_user.username, path_slug=self.slug
        )

    def is_valid_markdown_link(self, string):
        pattern = r'^\[([^\]]+)\]\((https?:\/\/[^\s\)]+|[^\s\)]+)\)$'
        return bool(re.match(pattern, string))

    def extract_link(self, md_text):
        md = MarkdownIt()
        tokens = md.parseInline(md_text)

        link_data = {}

        for token in tokens:
            if token.children: 
                for child in token.children:
                    if child.type == "link_open" and child.attrs:
                        # Extract href safely
                        attrs_dict = dict(child.attrs)
                        link_data["href"] = attrs_dict.get("href")
                    elif child.type == "text":
                        link_data["text"] = child.content  # Extract the link text
                    if "href" in link_data and "text" in link_data:
                        return link_data

        return {} 

    def slugify(title):
        return slugify_func(title)


like_list_user_bridge = db.Table(
    "like_list_user_bridge",
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "like_list_id",
        db.Integer,
        db.ForeignKey("like_lists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class LikeList(PkModel):

    __tablename__ = "like_lists"

    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False)
    users = db.relationship(
        "User",
        secondary=like_list_user_bridge,
        backref="user_like_lists",
    )


bookmark_list_user_bridge = db.Table(
    "bookmark_list_user_bridge",
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "bookmark_list_id",
        db.Integer,
        db.ForeignKey("bookmark_lists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class BookmarkList(PkModel):

    __tablename__ = "bookmark_lists"

    path_id = db.Column(db.Integer, db.ForeignKey("paths.id", ondelete="CASCADE"), nullable=False)
    users = db.relationship(
        "User",
        secondary=bookmark_list_user_bridge,
        backref="user_bookmark_lists",
    )


class Section(PkModel):

    __tablename__ = "sections"

    title = db.Column(db.String(200), nullable=False)
    links = db.relationship("Link", backref="link_section", lazy=True, cascade="all, delete-orphan")
    path_id = db.Column(
        db.Integer, db.ForeignKey("paths.id"), nullable=False
    )  # noqa: E128


class Link(PkModel):

    __tablename__ = "links"

    url = db.Column(db.String(500), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey("sections.id"), nullable=False
    )  # noqa: W292


class Emoji(PkModel):

    __tablename__ = "emoji_classes"

    class_name = db.Column(db.String(100), nullable=False)



class ActivationCode(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    plan = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<ActivationCode {self.code} for {self.plan}>'