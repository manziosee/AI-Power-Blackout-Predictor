"""ivr_calls — Feature 8

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ivr_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("language", sa.String(5), server_default="en"),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("call_status", sa.String(20), server_default="queued"),
        sa.Column("call_sid", sa.String(100), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ivr_calls_phone", "ivr_calls", ["phone"])


def downgrade() -> None:
    op.drop_index("ix_ivr_calls_phone", "ivr_calls")
    op.drop_table("ivr_calls")
