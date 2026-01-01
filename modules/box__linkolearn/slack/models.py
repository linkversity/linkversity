from init import db
from shopyo.api.models import PkModel

class SlackUser(PkModel):
    __tablename__ = "slack_users"
    
    slack_user_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("slack_account", uselist=False))
