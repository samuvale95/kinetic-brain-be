"""add sync tables

Revision ID: add_sync_tables
Revises: 
Create Date: 2024-01-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_sync_tables'
down_revision = None  # Update with latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Create sync_conflicts table
    op.create_table(
        'sync_conflicts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('server_version', sa.String(length=255), nullable=True),
        sa.Column('client_version', sa.String(length=255), nullable=True),
        sa.Column('server_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('client_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resolution', sa.String(length=50), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_conflicts_id'), 'sync_conflicts', ['id'], unique=False)
    op.create_index(op.f('ix_sync_conflicts_user_id'), 'sync_conflicts', ['user_id'], unique=False)
    op.create_index(op.f('ix_sync_conflicts_resolved'), 'sync_conflicts', ['resolved'], unique=False)
    
    # Create sync_history table
    op.create_table(
        'sync_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('changes_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('conflicts_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('client_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_type', sa.String(length=50), server_default='full', nullable=True),
        sa.Column('success', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_history_id'), 'sync_history', ['id'], unique=False)
    op.create_index(op.f('ix_sync_history_user_id'), 'sync_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_sync_history_synced_at'), 'sync_history', ['synced_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_sync_history_synced_at'), table_name='sync_history')
    op.drop_index(op.f('ix_sync_history_user_id'), table_name='sync_history')
    op.drop_index(op.f('ix_sync_history_id'), table_name='sync_history')
    op.drop_table('sync_history')
    
    op.drop_index(op.f('ix_sync_conflicts_resolved'), table_name='sync_conflicts')
    op.drop_index(op.f('ix_sync_conflicts_user_id'), table_name='sync_conflicts')
    op.drop_index(op.f('ix_sync_conflicts_id'), table_name='sync_conflicts')
    op.drop_table('sync_conflicts')
