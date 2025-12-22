"""add notification tables

Revision ID: c8d9e0f1a2b3
Revises: 1d8a5ec2e7b2
Create Date: 2025-01-15 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "1d8a5ec2e7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        # Email preferences
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_workout_reminders", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_new_workout", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_workout_completed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_plan_updates", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_weekly_generation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # Push preferences
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_workout_reminders", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_new_workout", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_workout_completed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_plan_updates", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_weekly_generation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_notification_preferences_user_id", "notification_preferences", ["user_id"])
    
    # Create device_tokens table
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_token", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("app_version", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "device_token", "platform", name="uq_device_tokens_user_token_platform"),
        sa.CheckConstraint("platform IN ('ios', 'android', 'web')", name="chk_device_tokens_platform"),
    )
    op.create_index("idx_device_tokens_user_id", "device_tokens", ["user_id"])
    op.create_index("idx_device_tokens_active", "device_tokens", ["user_id", "is_active"], 
                    postgresql_where=sa.text("is_active = true"))
    op.create_index("idx_device_tokens_platform", "device_tokens", ["platform", "is_active"],
                    postgresql_where=sa.text("is_active = true"))


def downgrade() -> None:
    op.drop_index("idx_device_tokens_platform", table_name="device_tokens")
    op.drop_index("idx_device_tokens_active", table_name="device_tokens")
    op.drop_index("idx_device_tokens_user_id", table_name="device_tokens")
    op.drop_table("device_tokens")
    op.drop_index("idx_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")

