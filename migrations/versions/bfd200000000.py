from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bfd200000000'
down_revision = '9b1b03d06a0a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subscription_plan', sa.Integer(), nullable=True, server_default='0'))

def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('subscription_plan')