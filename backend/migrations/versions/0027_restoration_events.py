"""0027 restoration events

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def _is_pg():
    return op.get_bind().dialect.name == "postgresql"


def _uuid_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import UUID
        return UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    op.create_table(
        "restoration_events",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("outage_report_id", _uuid_col(),
                  sa.ForeignKey("outage_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("utility_id", _uuid_col(),
                  sa.ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="reported"),
        sa.Column("eta_minutes", sa.Integer(), nullable=True),
        sa.Column("crew_count", sa.Integer(), nullable=True),
        sa.Column("crew_reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_restoration_outage_id", "restoration_events", ["outage_report_id"])
    op.create_index("ix_restoration_h3_index", "restoration_events", ["h3_index"])


def downgrade() -> None:
    op.drop_table("restoration_events")
