"""Add OAuth support

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add OAuth columns to users table
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(), default='email'))
    op.alter_column('users', 'password_hash', nullable=True)
    
    # Create oauth_accounts table
    op.create_table('oauth_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('provider_account_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oauth_accounts_id'), 'oauth_accounts', ['id'], unique=False)
    
    # Create unique constraint for provider + provider_account_id
    op.create_unique_constraint('uq_oauth_provider_account', 'oauth_accounts', ['provider', 'provider_account_id'])


def downgrade() -> None:
    # Drop oauth_accounts table
    op.drop_constraint('uq_oauth_provider_account', 'oauth_accounts', type_='unique')
    op.drop_index(op.f('ix_oauth_accounts_id'), table_name='oauth_accounts')
    op.drop_table('oauth_accounts')
    
    # Remove OAuth columns from users table
    op.alter_column('users', 'password_hash', nullable=False)
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'avatar_url')
