"""add strava sync jobs table

Revision ID: f3b2e0c91123
Revises: e54decaaad15
Create Date: 2025-11-07 22:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b2e0c91123"
down_revision: Union[str, None] = "e54decaaad15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strava_sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strava_account_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False, server_default="initial_sync"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("total_activities", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_activities", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_phase", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_phases_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_days_back", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_strava_sync_jobs_user_id", ondelete="CASCADE"),  # type: ignore[arg-type]
        sa.ForeignKeyConstraint(["strava_account_id"], ["strava_accounts.id"], name="fk_strava_sync_jobs_account_id", ondelete="CASCADE"),  # type: ignore[arg-type]
    )
    op.create_index("ix_strava_sync_jobs_user_id", "strava_sync_jobs", ["user_id"])
    op.create_index("ix_strava_sync_jobs_strava_account_id", "strava_sync_jobs", ["strava_account_id"])


def downgrade() -> None:
    op.drop_index("ix_strava_sync_jobs_strava_account_id", table_name="strava_sync_jobs")
    op.drop_index("ix_strava_sync_jobs_user_id", table_name="strava_sync_jobs")
    op.drop_table("strava_sync_jobs")

