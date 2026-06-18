"""0022 grid load snapshots

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def _uuid_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import UUID
        return UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    op.create_table(
        "grid_load_snapshots",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("load_mw", sa.Float(), nullable=True),
        sa.Column("capacity_mw", sa.Float(), nullable=True),
        sa.Column("load_pct", sa.Float(), nullable=True),
        sa.Column("renewable_pct", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_grid_load_region", "grid_load_snapshots", ["region"])
    op.create_index("ix_grid_load_recorded_at", "grid_load_snapshots", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("grid_load_snapshots")


def _is_pg():
    return op.get_bind().dialect.name == "postgresql"
