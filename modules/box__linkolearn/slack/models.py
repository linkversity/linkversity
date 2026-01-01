from init import db
from shopyo.api.models import PkModel

class SlackWorkspace(PkModel):
    __tablename__ = "slack_workspaces"
    
    team_id = db.Column(db.String(50), unique=True, nullable=False)
    team_name = db.Column(db.String(200))
    bot_token = db.Column(db.String(200), nullable=False)

class SlackUser(PkModel):
    __tablename__ = "slack_users"
    
    slack_user_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("slack_account", uselist=False))
    
    team_id = db.Column(db.String(50), db.ForeignKey("slack_workspaces.team_id"), nullable=True)