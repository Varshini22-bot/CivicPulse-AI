"""add_is_synthetic_geography_and_categories

Revision ID: 002
Revises: 001
Create Date: 2026-11-22 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. Categories table: add base_severity and keywords
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('base_severity', sa.Integer(), server_default='5', nullable=False))
        batch_op.add_column(sa.Column('keywords', sa.JSON(), server_default='[]', nullable=False))

    # 2. Reports table: add is_synthetic and location (PostGIS geography / SQLite text)
    geo_col = geoalchemy2.types.Geography(
        geometry_type='POINT',
        srid=4326,
        dimension=2,
        spatial_index=False,
        name='geography'
    ).with_variant(sa.Text(), 'sqlite')

    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_synthetic', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('location', geo_col, nullable=True))
        batch_op.create_index('ix_reports_is_synthetic', ['is_synthetic'], unique=False)
        batch_op.create_index('idx_reports_location_gist', ['location'], unique=False, postgresql_using='gist')

    # 3. Data population: backfill location from latitude/longitude
    if dialect == 'postgresql':
        op.execute(
            "UPDATE reports SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography "
            "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        op.execute("UPDATE reports SET is_synthetic = TRUE WHERE title LIKE '%[DEMO DATA]%'")
    else:
        op.execute(
            "UPDATE reports SET location = 'POINT(' || longitude || ' ' || latitude || ')' "
            "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        op.execute("UPDATE reports SET is_synthetic = 1 WHERE title LIKE '%[DEMO DATA]%'")


def downgrade() -> None:
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_index('idx_reports_location_gist')
        batch_op.drop_index('ix_reports_is_synthetic')
        batch_op.drop_column('location')
        batch_op.drop_column('is_synthetic')

    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('keywords')
        batch_op.drop_column('base_severity')
