import os
import sqlite3
from contextlib import contextmanager
from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


class EnterpriseDatabaseManager:
    @staticmethod
    def get_enterprise_db_uri(db_name: str) -> str:
        base_dir = current_app.config.get("BASE_DIR")
        db_dir = os.path.join(base_dir, "enterprise_dbs")
        os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{os.path.join(db_dir, db_name)}.db"

    @staticmethod
    def create_enterprise_database(db_name: str) -> str:
        uri = EnterpriseDatabaseManager.get_enterprise_db_uri(db_name)
        engine = create_engine(uri)

        from modules.box__linkolearn.linkolearn.models import Path, Section, Link
        from modules.box__default.auth.models import User

        Path.metadata.create_all(engine)
        Section.metadata.create_all(engine)
        Link.metadata.create_all(engine)

        return uri

    @staticmethod
    def get_enterprise_session(db_name: str):
        uri = EnterpriseDatabaseManager.get_enterprise_db_uri(db_name)
        engine = create_engine(uri)
        session_factory = sessionmaker(bind=engine)
        return scoped_session(session_factory())

    @staticmethod
    def delete_enterprise_database(db_name: str):
        base_dir = current_app.config.get("BASE_DIR")
        db_path = os.path.join(base_dir, "enterprise_dbs", f"{db_name}.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    @staticmethod
    def list_enterprises():
        from modules.box__default.auth.models import User

        return User.query.filter(
            User.enterprise_db_name.isnot(None), User.subscription_plan == 2
        ).all()


@contextmanager
def enterprise_db_session(db_name: str):
    session = EnterpriseDatabaseManager.get_enterprise_session(db_name)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.remove()
