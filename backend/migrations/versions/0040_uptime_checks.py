"""0040 create uptime_checks table

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    try:
        return "postgresql" in str(op.get_bind().engine.url)
    except Exception:
        return False


def upgrade() -> None:
    if _is_pg():
        op.create_table(
            "uptime_checks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("service", sa.String(60), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("response_ms", sa.Integer(), nullable=True),
            sa.Column("is_healthy", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    else:
        op.create_table(
            "uptime_checks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("service", sa.String(60), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("response_ms", sa.Integer(), nullable=True),
            sa.Column("is_healthy", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("checked_at", sa.DateTime(), server_default=sa.func.now()),
        )
    op.create_index("ix_uptime_checks_service", "uptime_checks", ["service"])
    op.create_index("ix_uptime_checks_checked_at", "uptime_checks", ["checked_at"])


def downgrade() -> None:
    op.drop_index("ix_uptime_checks_checked_at", table_name="uptime_checks")
    op.drop_index("ix_uptime_checks_service", table_name="uptime_checks")
    op.drop_table("uptime_checks")
