"""add strength_metrics to workout_sessions

Revision ID: add_strength_metrics
Revises: 
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_strength_metrics'
down_revision = None  # Update with latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Add strength_metrics JSON column to workout_sessions
    op.add_column('workout_sessions', 
                  sa.Column('strength_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove strength_metrics column
    op.drop_column('workout_sessions', 'strength_metrics')
