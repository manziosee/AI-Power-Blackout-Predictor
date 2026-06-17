"""data_export_requests — Feature 6

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_export_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_email", sa.String(255), nullable=False),
        sa.Column("requester_org", sa.String(200), nullable=True),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("h3_cells", JSONB(), nullable=True),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("format", sa.String(10), server_default="json"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("price_usd", sa.Float(), server_default="0.0"),
        sa.Column("paid", sa.Boolean(), server_default="false"),
        sa.Column("record_count", sa.Integer(), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("data_export_requests")
