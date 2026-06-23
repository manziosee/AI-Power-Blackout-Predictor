"""0033 outage incident clustering — new table + incident_id on outage_reports

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0033"
down_revision = "0032"
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
            "outage_incidents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("h3_cells", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("root_cause_estimate", sa.String(50), nullable=True),
            sa.Column("status", sa.String(20), server_default="active"),
            sa.Column("report_count", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    else:
        op.create_table(
            "outage_incidents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("h3_cells", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("root_cause_estimate", sa.String(50), nullable=True),
            sa.Column("status", sa.String(20), server_default="active"),
            sa.Column("report_count", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    with op.batch_alter_table("outage_reports") as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.String(36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("outage_reports") as batch_op:
        batch_op.drop_column("incident_id")
    op.drop_table("outage_incidents")
