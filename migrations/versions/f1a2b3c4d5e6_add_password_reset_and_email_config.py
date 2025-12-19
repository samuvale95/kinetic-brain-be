"""add_password_reset_and_email_config

Revision ID: f1a2b3c4d5e6
Revises: e54decaaad15
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e54decaaad15'
branch_labels = None
depends_on = None


def upgrade():
    # Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_id'), 'password_reset_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
    
    # Create email_config table (optional, for dynamic email configuration)
    op.create_table(
        'email_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('mail_username', sa.String(length=255), nullable=False),
        sa.Column('mail_password', sa.String(length=255), nullable=False),
        sa.Column('mail_from', sa.String(length=255), nullable=False),
        sa.Column('mail_from_name', sa.String(length=255), nullable=False),
        sa.Column('mail_port', sa.Integer(), nullable=False),
        sa.Column('mail_server', sa.String(length=255), nullable=False),
        sa.Column('mail_starttls', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('mail_ssl_tls', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('frontend_url', sa.String(length=500), nullable=True),
        sa.Column('admin_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_config_id'), 'email_config', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_email_config_id'), table_name='email_config')
    op.drop_table('email_config')
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_id'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
