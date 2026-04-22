"""Add enterprise encryption and settings

Revision ID: enterprise_encryption
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "enterprise_encryption"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "enterprise_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encryption_key", sa.String(256), nullable=True),
        sa.Column("custom_domain", sa.String(256), nullable=True),
        sa.Column("white_label_enabled", sa.Boolean(), default=False),
        sa.Column("analytics_enabled", sa.Boolean(), default=True),
        sa.Column("audit_log_enabled", sa.Boolean(), default=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    op.add_column("links", sa.Column("encrypted_url", sa.String(1000), nullable=True))
    op.add_column("links", sa.Column("is_encrypted", sa.Boolean(), default=False))

    op.add_column(
        "users", sa.Column("enterprise_db_name", sa.String(100), nullable=True)
    )
    op.add_column("users", sa.Column("team_id", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("users", "team_id")
    op.drop_column("users", "enterprise_db_name")
    op.drop_column("links", "is_encrypted")
    op.drop_column("links", "encrypted_url")
    op.drop_table("enterprise_settings")
