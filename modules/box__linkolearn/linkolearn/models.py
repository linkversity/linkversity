import datetime

from flask import url_for

from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from shopyo.api.models import PkModel
from modules.box__default.auth.models import EnterpriseTeam, User
from modules.box__linkolearn.linkolearn.enterprise_features import EnterpriseTeamMember
from init import db

import re
from markdown_it import MarkdownIt
from slugify import slugify as slugify_func


path_editor_bridge = db.Table(
    "path_editor_bridge",
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "path_id",
        db.Integer,
        db.ForeignKey("paths.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# User-pickable cover icons for paths (Font Awesome 5 free solid classes).
# Whitelist: anything stored here is later echoed into a `fas {{icon}}`
# class attribute, so the backend must only ever persist values from this
# list - never a raw client string. "" means "auto" (crc32-derived pick).
PATH_ICONS = [
    ("", "Auto"),
    ("fa-route", "Route"),
    ("fa-book-open", "Book"),
    ("fa-graduation-cap", "Study"),
    ("fa-code", "Code"),
    ("fa-palette", "Design"),
    ("fa-flask", "Science"),
    ("fa-lightbulb", "Ideas"),
    ("fa-rocket", "Launch"),
    ("fa-globe", "World"),
    ("fa-microscope", "Research"),
    ("fa-calculator", "Numbers"),
    ("fa-language", "Language"),
    ("fa-briefcase", "Business"),
    ("fa-heartbeat", "Health"),
    ("fa-camera", "Photo"),
    ("fa-compass", "Explore"),
    ("fa-laptop-code", "DevOps"),
    ("fa-trophy", "Goals"),
]
PATH_ICON_CLASSES = {cls for cls, _ in PATH_ICONS}

# (gradient start, gradient end, FA5 icon) - auto rotation used when the path
# has no user-chosen cover_icon. fa-music deliberately replaced by fa-rocket.
COVER_TINTS = [
    ("#FF385C", "#FF8A5B", "fa-route"),
    ("#2C5C80", "#79B7D6", "fa-code"),
    ("#2F6B45", "#82BB92", "fa-book-open"),
    ("#8A6220", "#DDB567", "fa-palette"),
    ("#4A4778", "#A5A2D4", "fa-flask"),
    ("#8C3B57", "#D899B0", "fa-rocket"),
    ("#96432A", "#E5A07F", "fa-graduation-cap"),
    ("#3E6E7E", "#8FC0CC", "fa-lightbulb"),
]


class Path(PkModel):
    __tablename__ = "paths"

    slug = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    # chosen cover icon (FA5 class from PATH_ICONS); NULL/"" = auto-derived
    cover_icon = db.Column(db.String(50), nullable=True)
    sections = db.relationship(
        "Section", backref="section_path", lazy=True, cascade="all, delete-orphan"
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("enterprise_teams.id"), nullable=True)
    is_visible = db.Column(db.Boolean, default=True)
    # enterprise option: no preview generation for links added to this path
    disable_previews = db.Column(db.Boolean, default=False, server_default="0")

    # Password for protection
    _password = db.Column(db.String(128), nullable=True)

    # Optional: Enforce password protection at creation
    is_password_protected = db.Column(db.Boolean, default=False)

    # Relationships
    like_list = db.relationship(
        "LikeList", backref="like_list_path", lazy=True, uselist=False
    )
    bookmark_list = db.relationship(
        "BookmarkList", backref="bookmark_list_path", lazy=True, uselist=False
    )

    editors = db.relationship(
        "User", secondary=path_editor_bridge, backref="editable_paths", lazy="dynamic"
    )

    def add_editor(self, user):
        if user not in self.editors:
            self.editors.append(user)

    def remove_editor(self, user):
        if user in self.editors:
            self.editors.remove(user)

    def is_org_member(self, user):
        """True when the user belongs to this path's organization (any role)."""
        if not self.team_id or user is None:
            return False
        if not getattr(user, "is_authenticated", False):
            return False
        team = EnterpriseTeam.query.get(self.team_id)
        if team and team.owner_id == user.id:
            return True
        return (
            EnterpriseTeamMember.query.filter_by(
                team_id=self.team_id, user_id=user.id
            ).first()
            is not None
        )

    def can_edit(self, user):
        """Owner, explicit editor, or org member with an admin/member role.

        Adding someone to the organization grants them access to every
        path owned by that organization.
        """
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        if user == self.path_user or user in self.editors:
            return True
        if not self.team_id:
            return False
        team = EnterpriseTeam.query.get(self.team_id)
        if team and team.owner_id == user.id:
            return True
        member = EnterpriseTeamMember.query.filter_by(
            team_id=self.team_id, user_id=user.id
        ).first()
        return member is not None and member.role in ("admin", "member")

    def is_team_path(self):
        return self.team_id is not None

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

    def get_org(self):
        """The organization this path belongs to, if any."""
        if self.team_id:
            from modules.box__default.auth.models import EnterpriseTeam

            return EnterpriseTeam.query.get(self.team_id)
        return None

    def get_url(self):
        # org-linked paths live under the organization's public page
        if self.team_id:
            from modules.box__default.auth.models import EnterpriseTeam

            team = EnterpriseTeam.query.get(self.team_id)
            if team and team.slug:
                return url_for(
                    "www.org_path", org_slug=team.slug, path_slug=self.slug
                )
        return url_for(
            "www.path", username=self.path_user.username, path_slug=self.slug
        )

    def cover_style(self):
        """(gradient_css, icon_class, monogram) for this path's cover.

        Single source of truth shared by the landing cards and the path
        profile header, so a path always looks the same everywhere.

        The user-chosen cover_icon wins; otherwise crc32(slug) picks from
        COVER_TINTS. crc32, not hash() - hash() is salted per process and
        would reshuffle colors on every restart.
        """
        import zlib

        seed = zlib.crc32((self.slug or str(self.id)).encode("utf-8"))
        c1, c2, icon = COVER_TINTS[seed % len(COVER_TINTS)]

        chosen = (self.cover_icon or "").strip()
        if chosen and chosen in PATH_ICON_CLASSES:
            icon = chosen

        title = (self.title or self.slug or "").strip() or (self.slug or "?")
        monogram = next((c.upper() for c in title if c.isalnum()), "?")

        grad = "linear-gradient(135deg, {}, {} 75%)".format(c1, c2)
        return grad, icon, monogram

    def cover_link_count(self):
        """Total links across all sections (for the cover count pill)."""
        return sum(len(s.links) for s in self.sections)

    def is_valid_markdown_link(self, string):
        pattern = r"^\[([^\]]+)\]\((https?:\/\/[^\s\)]+|[^\s\)]+)\)$"
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

    path_id = db.Column(
        db.Integer, db.ForeignKey("paths.id", ondelete="CASCADE"), nullable=False
    )
    users = db.relationship(
        "User",
        secondary=bookmark_list_user_bridge,
        backref="user_bookmark_lists",
    )


class Section(PkModel):
    __tablename__ = "sections"

    title = db.Column(db.String(200), nullable=False)
    links = db.relationship(
        "Link", backref="link_section", lazy=True, cascade="all, delete-orphan"
    )
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False)  # noqa: E128


class Link(PkModel):
    __tablename__ = "links"

    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    encrypted_url = db.Column(db.String(1000), nullable=True)
    is_encrypted = db.Column(db.Boolean, default=False)

    def get_url(self):
        if self.is_encrypted and self.encrypted_url:
            return self.decrypt_url()
        return self.url

    def set_encrypted_url(self, encryption_key):
        if encryption_key:
            from modules.box__linkolearn.linkolearn.encryption import encrypt_url

            self.encrypted_url = encrypt_url(self.url, encryption_key)
            self.is_encrypted = True

    def decrypt_url(self, encryption_key=None):
        if self.is_encrypted and self.encrypted_url:
            from modules.box__linkolearn.linkolearn.encryption import decrypt_url

            return decrypt_url(self.encrypted_url, encryption_key)
        return self.url


class Emoji(PkModel):
    __tablename__ = "emoji_classes"

    class_name = db.Column(db.String(100), nullable=False)


class ActivationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    plan = db.Column(db.Integer, nullable=False)

    @property
    def plan_type(self):
        return self.plan

    @property
    def plan_type_name(self):
        return {1: "Pro", 2: "Enterprise"}.get(self.plan, "Unknown")

    def __repr__(self):
        return f"<ActivationCode {self.code} for {self.plan}>"
