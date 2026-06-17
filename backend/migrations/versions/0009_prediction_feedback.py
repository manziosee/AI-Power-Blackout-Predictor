"""prediction_feedback — Feature 2

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("prediction_id", UUID(as_uuid=True),
                  sa.ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("outage_occurred", sa.Boolean(), nullable=True),
        sa.Column("sms_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_prediction_feedback_h3", "prediction_feedback", ["h3_index"])


def downgrade() -> None:
    op.drop_index("ix_prediction_feedback_h3", "prediction_feedback")
    op.drop_table("prediction_feedback")
