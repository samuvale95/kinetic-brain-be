"""remove_legacy_performance_fields

Revision ID: e54decaaad15
Revises: ad1103fc82e7
Create Date: 2025-10-29 17:59:56.832675

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e54decaaad15'
down_revision = 'ad1103fc82e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop legacy columns from performance_metrics
    with op.batch_alter_table('performance_metrics') as batch_op:
        # Old generic columns
        batch_op.drop_column('metric_type')
        batch_op.drop_column('threshold_value')
        batch_op.drop_column('max_value')
        batch_op.drop_column('rest_value')
        batch_op.drop_column('zones_json')


def downgrade() -> None:
    # Recreate legacy columns on performance_metrics (best-effort types)
    with op.batch_alter_table('performance_metrics') as batch_op:
        batch_op.add_column(sa.Column('zones_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('rest_value', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('max_value', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('threshold_value', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('metric_type', sa.String(length=20), nullable=True))
