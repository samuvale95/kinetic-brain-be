"""merge notification and password reset heads

Revision ID: 53fe423887be
Revises: f1a2b3c4d5e6, c8d9e0f1a2b3
Create Date: 2025-12-22 12:05:22.216034

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '53fe423887be'
down_revision = ('f1a2b3c4d5e6', 'c8d9e0f1a2b3')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
