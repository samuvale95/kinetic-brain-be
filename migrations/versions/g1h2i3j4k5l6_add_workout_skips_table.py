"""add_workout_skips_table

Revision ID: g1h2i3j4k5l6
Revises: c8d9e0f1a2b3
Create Date: 2025-01-24

"""
from alembic import op
import sqlalchemy as sa


revision = 'g1h2i3j4k5l6'
down_revision = 'c8d9e0f1a2b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workout_skips',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workout_id', sa.Integer(), sa.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skipped_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('workout_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_workout_skips_user_id', 'workout_skips', ['user_id'], unique=False)
    op.create_index('ix_workout_skips_workout_id', 'workout_skips', ['workout_id'], unique=False)
    op.create_index('ix_workout_skips_skipped_at', 'workout_skips', ['skipped_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workout_skips_skipped_at', table_name='workout_skips')
    op.drop_index('ix_workout_skips_workout_id', table_name='workout_skips')
    op.drop_index('ix_workout_skips_user_id', table_name='workout_skips')
    op.drop_table('workout_skips')
