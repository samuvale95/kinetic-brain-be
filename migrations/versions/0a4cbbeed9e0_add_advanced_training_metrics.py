"""add advanced training metrics tables

Revision ID: 0a4cbbeed9e0
Revises: e54decaaad15
Create Date: 2025-11-11 19:01:52.123456
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0a4cbbeed9e0"
down_revision = "b67b0c4d9ea2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_readiness_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("hrv_baseline", sa.Float(), nullable=True),
        sa.Column("hrv_value", sa.Float(), nullable=True),
        sa.Column("hrv_delta", sa.Float(), nullable=True),
        sa.Column("rhr_baseline", sa.Float(), nullable=True),
        sa.Column("rhr_value", sa.Float(), nullable=True),
        sa.Column("rhr_delta", sa.Float(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("sleep_quality_score", sa.Float(), nullable=True),
        sa.Column("epoc", sa.Float(), nullable=True),
        sa.Column("recovery_index", sa.Float(), nullable=True),
        sa.Column("readiness_state", sa.String(length=32), nullable=True),
        sa.Column("hydration_status", sa.String(length=32), nullable=True),
        sa.Column("hydration_score", sa.Float(), nullable=True),
        sa.Column("nutrition_score", sa.Float(), nullable=True),
        sa.Column("weight_delta_kg", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "metric_date", name="uq_daily_readiness_user_date"),
    )
    op.create_index(
        op.f("ix_daily_readiness_metrics_id"),
        "daily_readiness_metrics",
        ["id"],
        unique=False,
    )

    op.create_table(
        "weekly_training_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("total_duration_minutes", sa.Float(), nullable=True),
        sa.Column("total_distance_km", sa.Float(), nullable=True),
        sa.Column("total_tss", sa.Float(), nullable=True),
        sa.Column("multi_sport_load", sa.Float(), nullable=True),
        sa.Column("sport_breakdown", sa.JSON(), nullable=True),
        sa.Column("zone_distribution", sa.JSON(), nullable=True),
        sa.Column("high_intensity_ratio", sa.Float(), nullable=True),
        sa.Column("high_intensity_sessions", sa.Integer(), nullable=True),
        sa.Column("longest_workout_duration_minutes", sa.Float(), nullable=True),
        sa.Column("longest_workout_distance_km", sa.Float(), nullable=True),
        sa.Column("long_workout_progression_pct", sa.Float(), nullable=True),
        sa.Column("readiness_score", sa.Float(), nullable=True),
        sa.Column("injury_risk_score", sa.Float(), nullable=True),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("hydration_score", sa.Float(), nullable=True),
        sa.Column("plan_adherence_details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_training_summary_user_week"),
    )
    op.create_index(
        op.f("ix_weekly_training_summaries_id"),
        "weekly_training_summaries",
        ["id"],
        unique=False,
    )

    op.create_table(
        "metrics_pending_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_metrics_pending_jobs_status_priority",
        "metrics_pending_jobs",
        ["status", "priority", "available_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metrics_pending_jobs_id"),
        "metrics_pending_jobs",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_metrics_pending_jobs_id"), table_name="metrics_pending_jobs")
    op.drop_index("ix_metrics_pending_jobs_status_priority", table_name="metrics_pending_jobs")
    op.drop_table("metrics_pending_jobs")

    op.drop_index(op.f("ix_weekly_training_summaries_id"), table_name="weekly_training_summaries")
    op.drop_table("weekly_training_summaries")

    op.drop_index(op.f("ix_daily_readiness_metrics_id"), table_name="daily_readiness_metrics")
    op.drop_table("daily_readiness_metrics")

