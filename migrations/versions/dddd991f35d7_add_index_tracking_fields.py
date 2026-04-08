"""Add index tracking fields

Revision ID: dddd991f35d7
Revises: 0e3b811dbcf2
Create Date: 2026-04-07 00:06:01.695328

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dddd991f35d7'
down_revision = '0e3b811dbcf2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_indexed', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('last_indexed_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('stories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_indexed', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('last_indexed_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('stories', schema=None) as batch_op:
        batch_op.drop_column('last_indexed_at')
        batch_op.drop_column('is_indexed')

    with op.batch_alter_table('rules', schema=None) as batch_op:
        batch_op.drop_column('last_indexed_at')
        batch_op.drop_column('is_indexed')
