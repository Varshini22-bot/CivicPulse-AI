"""add_cv_pipeline_fields_and_feedback

Revision ID: 003
Revises: 002
Create Date: 2026-11-22 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('ai_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('suggested_category_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('detections', sa.JSON(), server_default='[]', nullable=True))
        batch_op.add_column(sa.Column('policy_note', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('is_overridden', sa.Boolean(), server_default=sa.false(), nullable=True))
        batch_op.add_column(sa.Column('override_category_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('override_user_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('override_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('override_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ai_predictions', schema=None) as batch_op:
        batch_op.drop_column('override_at')
        batch_op.drop_column('override_notes')
        batch_op.drop_column('override_user_id')
        batch_op.drop_column('override_category_id')
        batch_op.drop_column('is_overridden')
        batch_op.drop_column('policy_note')
        batch_op.drop_column('detections')
        batch_op.drop_column('suggested_category_id')
