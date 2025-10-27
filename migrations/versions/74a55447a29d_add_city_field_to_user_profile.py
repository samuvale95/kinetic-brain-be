"""Add city field to user_profile

Revision ID: 74a55447a29d
Revises: 001
Create Date: 2025-10-27 10:01:09.435457

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '74a55447a29d'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('city', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'city')
