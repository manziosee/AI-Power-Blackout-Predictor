"""planned_outages — Feature 1

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planned_outages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("utility_id", UUID(as_uuid=True),
                  sa.ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(20), server_default="manual"),
        sa.Column("external_id", sa.String(100), nullable=True, unique=True),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_planned_outages_h3", "planned_outages", ["h3_index"])


def downgrade() -> None:
    op.drop_index("ix_planned_outages_h3", "planned_outages")
    op.drop_table("planned_outages")
