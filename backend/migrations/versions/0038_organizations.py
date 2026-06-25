"""0038 create organizations table

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0038"
down_revision = "0037"
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
            "organizations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("plan", sa.String(30), nullable=False, server_default="free"),
            sa.Column("region", sa.String(20), nullable=False, server_default="global"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    else:
        op.create_table(
            "organizations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("plan", sa.String(30), nullable=False, server_default="free"),
            sa.Column("region", sa.String(20), nullable=False, server_default="global"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
