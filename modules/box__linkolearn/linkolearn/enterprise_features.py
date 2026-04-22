import datetime
from init import db


class EnterpriseAuditLog(db.Model):
    __tablename__ = "enterprise_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("enterprise_teams.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.now)

    @classmethod
    def log_action(
        cls,
        team_id: int,
        user_id: int,
        action: str,
        entity_type: str = None,
        entity_id: int = None,
        details: str = None,
        ip_address: str = None,
    ):
        log = cls(
            team_id=team_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        log.save()
        from init import db

        db.session.commit()
        return log


class EnterpriseAnalytics(db.Model):
    __tablename__ = "enterprise_analytics"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("enterprise_teams.id"), nullable=False
    )
    link_id = db.Column(db.Integer, db.ForeignKey("links.id"), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    event_count = db.Column(db.Integer, default=1)
    event_date = db.Column(
        db.DateTime(), nullable=False, default=datetime.datetime.now().date
    )
    referrer = db.Column(db.String(500), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    device_type = db.Column(db.String(50), nullable=True)

    @classmethod
    def track_click(
        cls,
        team_id: int,
        link_id: int,
        referrer: str = None,
        user_agent: str = None,
        country: str = None,
        device_type: str = None,
    ):
        today = datetime.datetime.now().date()
        existing = cls.query.filter_by(
            team_id=team_id, link_id=link_id, event_type="click", event_date=today
        ).first()

        if existing:
            existing.event_count += 1
            from init import db

            db.session.commit()
        else:
            from init import db

            event = cls(
                team_id=team_id,
                link_id=link_id,
                event_type="click",
                event_date=today,
                referrer=referrer,
                user_agent=user_agent,
                country=country,
                device_type=device_type,
            )
            db.session.add(event)
            db.session.commit()
        return existing or event

    def get_total_clicks(self, link_id: int = None, days: int = 30):
        query = EnterpriseAnalytics.query.filter_by(
            team_id=self.team_id, event_type="click"
        )
        if link_id:
            query = query.filter_by(link_id=link_id)

        since = datetime.datetime.now() - datetime.timedelta(days=days)
        return query.filter(EnterpriseAnalytics.event_date >= since).all()

    def get_top_links(self, limit: int = 10):
        from sqlalchemy import func

        return (
            db.session.query(
                EnterpriseAnalytics.link_id,
                func.sum(EnterpriseAnalytics.event_count).label("total"),
            )
            .filter(
                EnterpriseAnalytics.team_id == self.team_id,
                EnterpriseAnalytics.event_type == "click",
            )
            .group_by(EnterpriseAnalytics.link_id)
            .order_by(func.sum(EnterpriseAnalytics.event_count).desc())
            .limit(limit)
            .all()
        )


class EnterpriseTeamMember(db.Model):
    __tablename__ = "enterprise_team_members"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("enterprise_teams.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(50), default="member")
    joined_at = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.now)

    @classmethod
    def add_member(cls, team_id: int, user_id: int, role: str = "member"):
        from init import db

        member = cls(team_id=team_id, user_id=user_id, role=role)
        db.session.add(member)
        db.session.commit()
        return member

    def is_admin(self):
        return self.role == "admin"

    def is_viewer(self):
        return self.role == "viewer"


class EnterpriseCustomDomain(db.Model):
    __tablename__ = "enterprise_custom_domains"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("enterprise_teams.id"), nullable=False
    )
    domain = db.Column(db.String(256), nullable=False, unique=True)
    is_verified = db.Column(db.Boolean, default=False)
    ssl_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.now)

    @classmethod
    def add_domain(cls, team_id: int, domain: str):
        from init import db

        existing = cls.query.filter_by(domain=domain).first()
        if existing:
            return existing
        custom_domain = cls(team_id=team_id, domain=domain)
        db.session.add(custom_domain)
        db.session.commit()
        return custom_domain
