"""
.. module:: AdminModels
   :synopsis: Contains model of a user Record

"""

import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import AnonymousUserMixin
from flask_login import UserMixin
from init import login_manager
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from flask import current_app

from init import db
from shopyo.api.models import PkModel


role_user_bridge = db.Table(
    "role_user_bridge",
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "role_id",
        db.Integer,
        db.ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


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

    def __repr__(self):
        return f"<AnonymousUser {self.username}>"


login_manager.anonymous_user = AnonymousUser


class User(UserMixin, PkModel):
    """The user of the app"""

    __tablename__ = "users"

    username = db.Column(db.String(100), unique=True)
    _password = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(120), unique=True)
    date_registered = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.now()
    )
    is_email_confirmed = db.Column(db.Boolean(), nullable=False, default=False)
    email_confirm_date = db.Column(db.DateTime)
    emoji_class = db.Column(db.String(100), default="em-airplane")
    subscription_plan = db.Column(db.Integer, default=0, nullable=True)
    api_token = db.Column(db.String(100), unique=True, nullable=True)
    enterprise_db_name = db.Column(db.String(100), nullable=True)
    team_id = db.Column(db.Integer, nullable=True)

    paths = db.relationship("Path", backref="path_user", lazy=True)

    # A user can have many roles and a role can have many users
    roles = db.relationship(
        "Role",
        secondary=role_user_bridge,
        backref="users",
    )

    def __repr__(self):
        return f"<User-id: {self.id}, User-email: {self.email}>"

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, plaintext):
        self._password = generate_password_hash(plaintext, method="sha256")

    def check_password(self, password):
        return check_password_hash(self._password, password)

    def generate_confirmation_token(self):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt=current_app.config["PASSWORD_SALT"])

    def confirm_token(self, token, expiration=3600):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        email = False
        try:
            email = serializer.loads(
                token,
                salt=current_app.config["PASSWORD_SALT"],
                max_age=expiration,
            )
        except Exception as e:
            print(f"\nShopyo-LOG, Error at confirm_token: {e}")
            return False

        if email != self.email:
            return False

        self.is_email_confirmed = True
        self.email_confirm_date = datetime.datetime.now()
        self.update()
        return True

    def get_bookmarked_paths(self):
        # Retrieve the user object
        from modules.box__linkolearn.linkolearn.models import (
            Path,
            BookmarkList,
            bookmark_list_user_bridge,
        )

        user = self

        if user:
            # Query the bookmark lists for the user, joining with Path directly
            # This will get all bookmarked paths for the user, avoiding None entries
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
        self.subscription_plan = plan
        db.session.commit()

    def is_pro(self):
        return self.subscription_plan == 1

    def is_enterprise(self):
        return self.subscription_plan == 2

    def get_api_token(self):
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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


login_manager.login_view = "auth.login"


class Role(PkModel):
    """A role for a user."""

    __tablename__ = "roles"
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Role-id: {self.id}, Role-name: {self.name}>"
