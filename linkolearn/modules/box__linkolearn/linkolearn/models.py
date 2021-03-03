from flask import url_for

from shopyo.api.models import PkModel
from init import db


class Path(PkModel):

    __tablename__ = "paths"
    slug = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    sections = db.relationship('Section', backref='section_path', lazy=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
        nullable=False)

    def get_url(self):
        return url_for('www.path', username=self.path_user.username, path_slug=self.slug)


class Section(PkModel):

    __tablename__ = "sections"

    title = db.Column(db.String(200), nullable=False)
    links = db.relationship('Link', backref='link_section', lazy=True)
    path_id = db.Column(db.Integer, db.ForeignKey('paths.id'),
        nullable=False)  # noqa: E128


class Link(PkModel):

    __tablename__ = 'links'

    url = db.Column(db.String(500), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'),
            nullable=False)  # noqa: W292