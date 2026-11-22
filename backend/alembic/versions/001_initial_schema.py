"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-11-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Departments
    op.create_table(
        'departments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='citizen'),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

    # 3. Categories (original schema)
    op.create_table(
        'categories',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_department_id', sa.String(length=36), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('icon', sa.String(length=50), server_default='alert-circle'),
        sa.Column('safety_weight', sa.Float(), server_default='0.5')
    )

    # 4. Staff
    op.create_table(
        'staff',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('department_id', sa.String(length=36), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('designation', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 5. Reports (original schema)
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('tracking_number', sa.String(length=50), nullable=False, unique=True),
        sa.Column('citizen_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category_id', sa.String(length=36), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('verified_category_id', sa.String(length=36), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('area', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Submitted'),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('resolution_image_url', sa.String(length=500), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('ai_severity', sa.Integer(), server_default='5'),
        sa.Column('human_severity', sa.Integer(), nullable=True),
        sa.Column('priority_score', sa.Float(), server_default='50.0'),
        sa.Column('priority_level', sa.String(length=20), server_default='Medium'),
        sa.Column('is_duplicate', sa.Boolean(), server_default=sa.false()),
        sa.Column('canonical_report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True)
    )

    # 6. AIPrediction
    op.create_table(
        'ai_predictions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=False, unique=True),
        sa.Column('predicted_category_id', sa.String(length=36), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('detected_features', sa.JSON(), nullable=True),
        sa.Column('raw_predictions', sa.JSON(), nullable=True),
        sa.Column('model_name', sa.String(length=100), server_default='CivicPulse-Vision-Ensemble-v1'),
        sa.Column('model_version', sa.String(length=50), server_default='1.2.0'),
        sa.Column('inference_time_ms', sa.Float(), server_default='45.0'),
        sa.Column('processing_status', sa.String(length=50), server_default='completed'),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 7. PriorityScores
    op.create_table(
        'priority_scores',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=False, unique=True),
        sa.Column('severity_component', sa.Float(), nullable=False),
        sa.Column('safety_component', sa.Float(), nullable=False),
        sa.Column('location_risk_component', sa.Float(), nullable=False),
        sa.Column('community_impact_component', sa.Float(), nullable=False),
        sa.Column('age_component', sa.Float(), nullable=False),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('priority_level', sa.String(length=20), nullable=False),
        sa.Column('explanation_json', sa.JSON(), nullable=False),
        sa.Column('scoring_version', sa.String(length=50), server_default='v1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 8. DuplicateCandidates
    op.create_table(
        'duplicate_candidates',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('source_report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('target_report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('distance_meters', sa.Float(), nullable=False),
        sa.Column('category_match', sa.Boolean(), server_default=sa.true()),
        sa.Column('time_diff_hours', sa.Float(), nullable=False),
        sa.Column('visual_similarity', sa.Float(), nullable=True),
        sa.Column('composite_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='suggested'),
        sa.Column('resolved_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 9. Assignments
    op.create_table(
        'assignments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('department_id', sa.String(length=36), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('staff_id', sa.String(length=36), sa.ForeignKey('staff.id'), nullable=True),
        sa.Column('assigned_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 10. AuditLogs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('previous_state', sa.JSON(), nullable=True),
        sa.Column('new_state', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )

    # 11. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.false()),
        sa.Column('notification_type', sa.String(length=50), server_default='info'),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('assignments')
    op.drop_table('duplicate_candidates')
    op.drop_table('priority_scores')
    op.drop_table('ai_predictions')
    op.drop_table('reports')
    op.drop_table('staff')
    op.drop_table('categories')
    op.drop_table('users')
    op.drop_table('departments')
