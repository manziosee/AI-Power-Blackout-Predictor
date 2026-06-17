"""prepaid_meters + prepaid_topup_reminders — Feature 10

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prepaid_meters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meter_number", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("last_balance_kwh", sa.Float(), nullable=True),
        sa.Column("low_balance_threshold_kwh", sa.Float(), server_default="10.0"),
        sa.Column("alert_before_hours", sa.Integer(), server_default="12"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "meter_number", name="uq_prepaid_meter_user_number"),
    )
    op.create_index("ix_prepaid_meters_user_id", "prepaid_meters", ["user_id"])

    op.create_table(
        "prepaid_topup_reminders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("meter_id", UUID(as_uuid=True),
                  sa.ForeignKey("prepaid_meters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prediction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("message_sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("balance_at_send", sa.Float(), nullable=True),
        sa.Column("topup_detected", sa.Boolean(), server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("prepaid_topup_reminders")
    op.drop_index("ix_prepaid_meters_user_id", "prepaid_meters")
    op.drop_table("prepaid_meters")
