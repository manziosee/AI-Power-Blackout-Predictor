"""white_label_configs — Feature 7

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "white_label_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("utility_id", UUID(as_uuid=True),
                  sa.ForeignKey("utility_companies.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("brand_name", sa.String(200), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(7), server_default="#2563EB"),
        sa.Column("secondary_color", sa.String(7), server_default="#1E40AF"),
        sa.Column("sms_sender_id", sa.String(11), nullable=True),
        sa.Column("email_from_name", sa.String(100), nullable=True),
        sa.Column("email_from_address", sa.String(255), nullable=True),
        sa.Column("custom_domain", sa.String(255), nullable=True),
        sa.Column("support_phone", sa.String(20), nullable=True),
        sa.Column("support_email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("white_label_configs")
