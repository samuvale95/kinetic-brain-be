"""add_performance_metrics_fields

Revision ID: ad1103fc82e7
Revises: 74a55447a29d
Create Date: 2025-10-29 17:16:51.128111

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad1103fc82e7'
down_revision = '74a55447a29d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make threshold_value and metric_type nullable (for backward compatibility and new unified structure)
    op.alter_column('performance_metrics', 'threshold_value', nullable=True)
    op.alter_column('performance_metrics', 'metric_type', nullable=True)
    
    # HR Metrics
    op.add_column('performance_metrics', sa.Column('hr_max', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('hr_rest', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('threshold_hr', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('hrr', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('custom_threshold_hr', sa.Float(), nullable=True))
    
    # Pace Metrics
    op.add_column('performance_metrics', sa.Column('threshold_pace', sa.String(length=10), nullable=True))
    op.add_column('performance_metrics', sa.Column('critical_speed', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('vla', sa.Float(), nullable=True))
    
    # Power Metrics
    op.add_column('performance_metrics', sa.Column('ftp', sa.Float(), nullable=True))
    op.add_column('performance_metrics', sa.Column('wkg', sa.Float(), nullable=True))
    
    # Advanced Metrics
    op.add_column('performance_metrics', sa.Column('vo2max', sa.Float(), nullable=True))
    
    # Structured Zones
    op.add_column('performance_metrics', sa.Column('hr_zones', sa.JSON(), nullable=True))
    op.add_column('performance_metrics', sa.Column('hr_zones_source', sa.String(length=10), nullable=True))
    op.add_column('performance_metrics', sa.Column('hr_threshold_used', sa.Float(), nullable=True))
    
    op.add_column('performance_metrics', sa.Column('pace_zones', sa.JSON(), nullable=True))
    op.add_column('performance_metrics', sa.Column('pace_zones_source', sa.String(length=10), nullable=True))
    op.add_column('performance_metrics', sa.Column('threshold_pace_used', sa.String(length=10), nullable=True))
    
    op.add_column('performance_metrics', sa.Column('power_zones', sa.JSON(), nullable=True))
    op.add_column('performance_metrics', sa.Column('power_zones_source', sa.String(length=10), nullable=True))
    op.add_column('performance_metrics', sa.Column('ftp_used', sa.Float(), nullable=True))
    
    # Add updated_at column
    op.add_column('performance_metrics', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove updated_at column
    op.drop_column('performance_metrics', 'updated_at')
    
    # Remove structured zones
    op.drop_column('performance_metrics', 'ftp_used')
    op.drop_column('performance_metrics', 'power_zones_source')
    op.drop_column('performance_metrics', 'power_zones')
    op.drop_column('performance_metrics', 'threshold_pace_used')
    op.drop_column('performance_metrics', 'pace_zones_source')
    op.drop_column('performance_metrics', 'pace_zones')
    op.drop_column('performance_metrics', 'hr_threshold_used')
    op.drop_column('performance_metrics', 'hr_zones_source')
    op.drop_column('performance_metrics', 'hr_zones')
    
    # Remove advanced metrics
    op.drop_column('performance_metrics', 'vo2max')
    
    # Remove power metrics
    op.drop_column('performance_metrics', 'wkg')
    op.drop_column('performance_metrics', 'ftp')
    
    # Remove pace metrics
    op.drop_column('performance_metrics', 'vla')
    op.drop_column('performance_metrics', 'critical_speed')
    op.drop_column('performance_metrics', 'threshold_pace')
    
    # Remove HR metrics
    op.drop_column('performance_metrics', 'custom_threshold_hr')
    op.drop_column('performance_metrics', 'hrr')
    op.drop_column('performance_metrics', 'threshold_hr')
    op.drop_column('performance_metrics', 'hr_rest')
    op.drop_column('performance_metrics', 'hr_max')
    
    # Make threshold_value and metric_type not nullable again
    op.alter_column('performance_metrics', 'threshold_value', nullable=False)
    op.alter_column('performance_metrics', 'metric_type', nullable=False)
