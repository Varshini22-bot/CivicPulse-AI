"""add_upvote_count_to_reports

Revision ID: 006
Revises: 005
Create Date: 2026-11-22 05:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, Sequence[str], None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('upvote_count', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_column('upvote_count')
