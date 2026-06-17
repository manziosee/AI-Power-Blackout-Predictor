"""insurance_policies + insurance_claims — Feature 5

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insurance_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("premium_usd_monthly", sa.Float(), nullable=False),
        sa.Column("payout_usd_per_hour", sa.Float(), nullable=False),
        sa.Column("min_duration_hours", sa.Float(), server_default="2.0"),
        sa.Column("max_payout_usd", sa.Float(), nullable=False),
        sa.Column("insurer", sa.String(50), server_default="platform"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_insurance_policies_h3", "insurance_policies", ["h3_index"])

    op.create_table(
        "insurance_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", UUID(as_uuid=True),
                  sa.ForeignKey("insurance_policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("outage_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outage_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_hours", sa.Float(), nullable=True),
        sa.Column("payout_usd", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_ref", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("insurance_claims")
    op.drop_index("ix_insurance_policies_h3", "insurance_policies")
    op.drop_table("insurance_policies")
