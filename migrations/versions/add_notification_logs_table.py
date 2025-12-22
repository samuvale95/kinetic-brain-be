"""add notification_logs table

Revision ID: add_notification_logs
Revises: 53fe423887be
Create Date: 2025-01-15 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_notification_logs"
down_revision: Union[str, None] = "53fe423887be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_logs table
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        
        # Notification details
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),  # email, push
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        
        # Status
        sa.Column("status", sa.String(length=20), nullable=False),  # sent, failed, skipped
        sa.Column("error_message", sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes
    op.create_index("idx_notification_logs_user_id", "notification_logs", ["user_id"])
    op.create_index("idx_notification_logs_sent_at", "notification_logs", ["sent_at"])
    op.create_index("idx_notification_logs_user_sent_at", "notification_logs", ["user_id", "sent_at"])
    op.create_index("idx_notification_logs_status", "notification_logs", ["status"])
    op.create_index("idx_notification_logs_type", "notification_logs", ["notification_type"])
    
    # Add check constraint for channel
    op.create_check_constraint(
        "chk_notification_logs_channel",
        "notification_logs",
        "channel IN ('email', 'push')"
    )
    
    # Add check constraint for status
    op.create_check_constraint(
        "chk_notification_logs_status",
        "notification_logs",
        "status IN ('sent', 'failed', 'skipped')"
    )


def downgrade() -> None:
    op.drop_index("idx_notification_logs_type", table_name="notification_logs")
    op.drop_index("idx_notification_logs_status", table_name="notification_logs")
    op.drop_index("idx_notification_logs_user_sent_at", table_name="notification_logs")
    op.drop_index("idx_notification_logs_sent_at", table_name="notification_logs")
    op.drop_index("idx_notification_logs_user_id", table_name="notification_logs")
    op.drop_constraint("chk_notification_logs_status", table_name="notification_logs", type_="check")
    op.drop_constraint("chk_notification_logs_channel", table_name="notification_logs", type_="check")
    op.drop_table("notification_logs")
