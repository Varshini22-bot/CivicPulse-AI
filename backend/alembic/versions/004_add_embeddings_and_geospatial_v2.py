"""add_embeddings_and_geospatial_v2

Revision ID: 004
Revises: 003
Create Date: 2026-11-22 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Road Segments table for OSM recurrence detection
    op.create_table(
        'road_segments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('osm_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('highway_type', sa.String(length=50), server_default='residential', nullable=False),
        sa.Column('ward', sa.String(length=100), nullable=True),
        sa.Column('geometry', sa.JSON(), nullable=False),
        sa.Column('length_meters', sa.Float(), server_default='100.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 2. Report Embeddings table for CLIP feature representations
    op.create_table(
        'report_embeddings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('model_name', sa.String(length=100), server_default='openclip-vit-b-32', nullable=False),
        sa.Column('dimension', sa.Integer(), server_default='512', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 3. Add road_segment_id to reports
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('road_segment_id', sa.String(length=36), nullable=True))

    # 4. Add v2 features to duplicate_candidates
    with op.batch_alter_table('duplicate_candidates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clip_similarity', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('phash_similarity', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('resolution_feedback', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('duplicate_candidates', schema=None) as batch_op:
        batch_op.drop_column('resolution_feedback')
        batch_op.drop_column('phash_similarity')
        batch_op.drop_column('clip_similarity')

    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_column('road_segment_id')

    op.drop_table('report_embeddings')
    op.drop_table('road_segments')
