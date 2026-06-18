"""0025 public api keys and usage

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def _is_pg():
    return op.get_bind().dialect.name == "postgresql"


def _uuid_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import UUID
        return UUID(as_uuid=True)
    return sa.String(36)


def _jsonb_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import JSONB
        return JSONB()
    return sa.Text()


def upgrade() -> None:
    op.create_table(
        "public_api_keys",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("organization", sa.String(200), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False, server_default="ngo"),
        sa.Column("allowed_regions", _jsonb_col(), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("rate_limit_per_day", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "public_api_usage",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("api_key_id", _uuid_col(), sa.ForeignKey("public_api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(200), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_public_api_usage_key_id", "public_api_usage", ["api_key_id"])
    op.create_index("ix_public_api_usage_created_at", "public_api_usage", ["created_at"])


def downgrade() -> None:
    op.drop_table("public_api_usage")
    op.drop_table("public_api_keys")
