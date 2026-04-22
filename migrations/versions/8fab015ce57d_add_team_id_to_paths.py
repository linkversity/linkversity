"""add_team_id_to_paths

Revision ID: 8fab015ce57d
Revises: b3c52d931b07
Create Date: 2026-04-22 11:16:12.393933

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8fab015ce57d"
down_revision = "b3c52d931b07"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("paths", sa.Column("team_id", sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    op.drop_column("paths", "team_id")

    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint("fk_paths_team_id", "paths", type_="foreignkey")
    op.drop_column("paths", "team_id")

    # ### end Alembic commands ###
