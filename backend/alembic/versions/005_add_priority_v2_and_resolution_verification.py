"""add_priority_v2_and_resolution_verification

Revision ID: 005
Revises: 004
Create Date: 2026-11-22 04:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, Sequence[str], None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add resolution verification and POI context columns to reports
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resolution_verification_status', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('resolution_verification_details', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('location_risk_poi_details', sa.JSON(), nullable=True))

    # 2. Add continuous age and POI bonus metrics to priority_scores
    with op.batch_alter_table('priority_scores', schema=None) as batch_op:
        batch_op.add_column(sa.Column('age_saturating_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('poi_proximity_bonus', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('priority_scores', schema=None) as batch_op:
        batch_op.drop_column('poi_proximity_bonus')
        batch_op.drop_column('age_saturating_score')

    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_column('location_risk_poi_details')
        batch_op.drop_column('resolution_verification_details')
        batch_op.drop_column('resolution_verification_status')
