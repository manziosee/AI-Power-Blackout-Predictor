"""platform ops — admin flag, location alert settings, fraud_flags

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: admin flag ─────────────────────────────────────────────────────
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False))

    # ── user_locations: per-location alert settings ───────────────────────────
    op.add_column("user_locations", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("user_locations", sa.Column("alert_threshold", sa.Float(), server_default="0.70", nullable=False))
    op.add_column("user_locations", sa.Column("quiet_hours_start", sa.Time(), nullable=True))
    op.add_column("user_locations", sa.Column("quiet_hours_end", sa.Time(), nullable=True))
    op.add_column("user_locations", sa.Column("notify_channels", JSONB(), server_default='["sms","push"]', nullable=False))

    # ── fraud_flags ───────────────────────────────────────────────────────────
    op.create_table(
        "fraud_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("report_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rule", sa.String(50), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(10), server_default="medium"),
        sa.Column("resolved", sa.Boolean(), server_default="false"),
        sa.Column("resolved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_fraud_user", "fraud_flags", ["user_id"])
    op.create_index("idx_fraud_created", "fraud_flags", ["created_at"])
    op.create_index("idx_fraud_unresolved", "fraud_flags", ["resolved", "created_at"])


def downgrade() -> None:
    op.drop_table("fraud_flags")
    op.drop_column("user_locations", "notify_channels")
    op.drop_column("user_locations", "quiet_hours_end")
    op.drop_column("user_locations", "quiet_hours_start")
    op.drop_column("user_locations", "alert_threshold")
    op.drop_column("user_locations", "is_active")
    op.drop_column("users", "is_admin")
