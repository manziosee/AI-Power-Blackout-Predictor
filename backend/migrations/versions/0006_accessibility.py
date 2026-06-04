"""0006 accessibility — sms_inbound_log

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sms_inbound_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("message", sa.String(160), nullable=False),
        sa.Column("command", sa.String(20), nullable=False),
        sa.Column("reply", sa.String(160), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sms_inbound_log_phone",    "sms_inbound_log", ["phone"])
    op.create_index("ix_sms_inbound_log_received", "sms_inbound_log", ["received_at"])


def downgrade() -> None:
    op.drop_table("sms_inbound_log")
