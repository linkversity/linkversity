"""add cover_icon to paths

Revision ID: 71f72b1115f6
Revises: a0698e947742
Create Date: 2026-10-21 17:05:12.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "71f72b1115f6"
down_revision = "a0698e947742"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("paths", sa.Column("cover_icon", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("paths", "cover_icon")
