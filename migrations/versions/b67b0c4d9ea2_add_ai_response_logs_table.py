"""add ai response logs table

Revision ID: b67b0c4d9ea2
Revises: f3b2e0c91123
Create Date: 2025-11-08 17:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b67b0c4d9ea2"
down_revision: Union[str, None] = "f3b2e0c91123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_response_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("parse_success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_response_logs_user_id", "ai_response_logs", ["user_id"])
    op.create_index("ix_ai_response_logs_request_type", "ai_response_logs", ["request_type"])


def downgrade() -> None:
    op.drop_index("ix_ai_response_logs_request_type", table_name="ai_response_logs")
    op.drop_index("ix_ai_response_logs_user_id", table_name="ai_response_logs")
    op.drop_table("ai_response_logs")



