"""seasonal_stats — Feature 12

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seasonal_stats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("outage_count", sa.Integer(), server_default="0"),
        sa.Column("avg_duration_minutes", sa.Float(), nullable=True),
        sa.Column("total_outage_hours", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("h3_index", "month", "year", name="uq_seasonal_h3_month_year"),
    )
    op.create_index("ix_seasonal_stats_h3", "seasonal_stats", ["h3_index"])


def downgrade() -> None:
    op.drop_index("ix_seasonal_stats_h3", "seasonal_stats")
    op.drop_table("seasonal_stats")
