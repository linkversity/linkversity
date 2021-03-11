from flask import url_for

from shopyo.api.models import PkModel
from modules.box__default.auth.models import User
from init import db


class Path(PkModel):

    __tablename__ = "paths"
    slug = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    sections = db.relationship("Section", backref="section_path", lazy=True, cascade="all, delete-orphan")

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    like_list = db.relationship(
        "LikeList", backref="like_list_path", lazy=True, uselist=False
    )
    bookmark_list = db.relationship(
        "BookmarkList", backref="bookmark_list_path", lazy=True, uselist=False
    )

    def get_url(self):
        return url_for(
            "www.path", username=self.path_user.username, path_slug=self.slug
        )


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

    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False)
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
