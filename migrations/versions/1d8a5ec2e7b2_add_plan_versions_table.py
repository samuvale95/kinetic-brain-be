"""add plan versions table

Revision ID: 1d8a5ec2e7b2
Revises: 0a4cbbeed9e0
Create Date: 2025-11-12 19:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1d8a5ec2e7b2"
down_revision = "0a4cbbeed9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_weeks", sa.Integer(), nullable=False),
        sa.Column("sport_type", sa.String(length=50), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=True),
        sa.Column("plan_payload", sa.JSON(), nullable=False),
        sa.Column("validator_violations", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["workout_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_versions_id"), "plan_versions", ["id"], unique=False)
    op.create_index("ix_plan_versions_user_id", "plan_versions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_plan_versions_user_id", table_name="plan_versions")
    op.drop_index(op.f("ix_plan_versions_id"), table_name="plan_versions")
    op.drop_table("plan_versions")

