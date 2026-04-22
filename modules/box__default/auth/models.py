"""
.. module:: AdminModels
   :synopsis: Contains model of a user Record

"""

import datetime
import hashlib
import logging
import secrets

from flask import current_app
from flask_login import AnonymousUserMixin
from flask_login import UserMixin
from sqlalchemy import func
from sqlalchemy.orm import object_session
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

# Import db and login_manager from init
from init import db
from init import login_manager

# Import User from shopyo_auth - this is the base User model
from shopyo_auth.models import User as BaseUser
from shopyo_auth.models import UserToken as BaseUserToken
from shopyo_auth.models import Role as BaseRole
from shopyo_auth.models import role_user_bridge
from itsdangerous import URLSafeTimedSerializer
from shopyo.api.models import PkModel


class AnonymousUser(AnonymousUserMixin):
    """Anonymous user class"""

    def __init__(self):
        self.username = "guest"
        self.email = "<anonymous-user-no-email>"

    @property
    def is_email_confirmed(self):
        is_disabled = False

        if "EMAIL_CONFIRMATION_DISABLED" in current_app.config:
            is_disabled = current_app.config["EMAIL_CONFIRMATION_DISABLED"]

            if is_disabled is not True:
                is_disabled = False

        return is_disabled

    @property
    def is_admin(self):
        return False

    @property
    def roles(self):
        return []

    def __repr__(self):
        return f"<AnonymousUser {self.username}>"


login_manager.anonymous_user = AnonymousUser


# Extend the shopyo_auth User model with Linkversity-specific fields
BaseUser.__table_args__ = {"extend_existing": True}

# Add Linkversity specific columns
BaseUser.emoji_class = db.Column(db.String(100), default="em-airplane")
BaseUser.subscription_plan = db.Column(db.Integer, default=0, nullable=True)
BaseUser.api_token = db.Column(db.String(100), unique=True, nullable=True)
BaseUser.enterprise_db_name = db.Column(db.String(100), nullable=True)
BaseUser.team_id = db.Column(db.Integer, nullable=True)

# Add the paths relationship
BaseUser.paths = db.relationship("Path", backref="path_user", lazy=True)

# Re-map the roles relationship to use the same bridge table
BaseUser.roles = db.relationship(
    "Role",
    secondary=role_user_bridge,
    backref="users",
)

# Use the base User, UserToken, Role from shopyo_auth
User = BaseUser
UserToken = BaseUserToken
Role = BaseRole


# Add Linkversity-specific methods to User
def is_pro(self):
    return self.subscription_plan is not None and self.subscription_plan >= 1


def is_enterprise(self):
    return self.subscription_plan is not None and self.subscription_plan == 2


def get_api_token_method(self):
    if not self.api_token:
        import secrets

        self.api_token = secrets.token_hex(16)
        self.update()
    return self.api_token


def is_enterprise_admin(self):
    return self.is_enterprise() and self.team_id is not None


def get_enterprise_settings(self):
    from modules.box__linkolearn.linkolearn.models import EnterpriseSettings

    return EnterpriseSettings.query.filter_by(user_id=self.id).first()


def create_enterprise_team(self, team_name: str):
    from init import db

    team = EnterpriseTeam(name=team_name, owner_id=self.id)
    team.save()
    self.team_id = team.id
    self.subscription_plan = 2
    db.session.commit()
    settings = EnterpriseSettings(user_id=self.id)
    settings.set_encryption_key()
    settings.save()
    return team


# Attach methods to User class
User.is_pro = is_pro
User.is_enterprise = is_enterprise
User.get_api_token = get_api_token_method
User.is_enterprise_admin = is_enterprise_admin
User.get_enterprise_settings = get_enterprise_settings
User.create_enterprise_team = create_enterprise_team


def get_first_name(self):
    if self.first_name in ["", None]:
        return "-first name-"
    else:
        return self.first_name


def get_last_name(self):
    if self.last_name in ["", None]:
        return "-last name-"
    else:
        return self.last_name


def get_profile_url(self):
    return f"/{self.username}"


def upgrade_subscription(self, plan: int):
    from init import db

    self.subscription_plan = plan
    db.session.commit()


def get_bookmarked_paths(self):
    from modules.box__linkolearn.linkolearn.models import (
        Path,
        BookmarkList,
        bookmark_list_user_bridge,
    )
    from init import db

    user = self
    if user:
        bookmarked_paths = (
            db.session.query(Path)
            .join(BookmarkList, BookmarkList.path_id == Path.id)
            .join(
                bookmark_list_user_bridge,
                bookmark_list_user_bridge.c.bookmark_list_id == BookmarkList.id,
            )
            .filter(bookmark_list_user_bridge.c.user_id == user.id)
            .all()
        )
        return bookmarked_paths
    else:
        return None


User.get_first_name = get_first_name
User.get_last_name = get_last_name
User.get_profile_url = get_profile_url
User.upgrade_subscription = upgrade_subscription
User.get_bookmarked_paths = get_bookmarked_paths


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


login_manager.login_view = "auth.login"


class EnterpriseTeam(PkModel):
    __tablename__ = "enterprise_teams"

    name = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False)

    def __init__(self, **kwargs):
        import datetime

        super().__init__(**kwargs)
        self.created_at = datetime.datetime.now()


class EnterpriseSettings(PkModel):
    __tablename__ = "enterprise_settings"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    encryption_key = db.Column(db.String(256), nullable=True)
    custom_domain = db.Column(db.String(256), nullable=True)
    white_label_enabled = db.Column(db.Boolean, default=False)
    analytics_enabled = db.Column(db.Boolean, default=True)
    audit_log_enabled = db.Column(db.Boolean, default=True)
    max_team_members = db.Column(db.Integer, default=10)

    def set_encryption_key(self):
        from modules.box__linkolearn.linkolearn.encryption import (
            generate_encryption_key,
        )

        self.encryption_key = generate_encryption_key()

    def get_fernet(self):
        from modules.box__linkolearn.linkolearn.encryption import get_fernet

        return get_fernet(self.encryption_key)
