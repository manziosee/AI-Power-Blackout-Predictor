"""regulatory_reports + dispatch_recommendations — Feature 14

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regulatory_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("country_code", sa.String(5), nullable=False),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("report_year", sa.Integer(), nullable=False),
        sa.Column("report_month", sa.Integer(), nullable=False),
        sa.Column("total_outages", sa.Integer(), server_default="0"),
        sa.Column("total_outage_hours", sa.Float(), nullable=True),
        sa.Column("uptime_pct", sa.Float(), nullable=True),
        sa.Column("affected_cells_count", sa.Integer(), server_default="0"),
        sa.Column("worst_cell_h3", sa.String(15), nullable=True),
        sa.Column("avg_repair_minutes", sa.Float(), nullable=True),
        sa.Column("report_data", JSONB(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("report_url", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "country_code", "district", "report_year", "report_month",
            name="uq_regulatory_report",
        ),
    )
    op.create_index("ix_regulatory_reports_country", "regulatory_reports", ["country_code"])

    op.create_table(
        "dispatch_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("utility_id", UUID(as_uuid=True),
                  sa.ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("high_risk_cells", JSONB(), nullable=False),
        sa.Column("recommended_positions", JSONB(), nullable=True),
        sa.Column("crew_count", sa.Integer(), server_default="1"),
        sa.Column("total_priority_score", sa.Float(), nullable=True),
        sa.Column("is_acknowledged", sa.Boolean(), server_default="false"),
        sa.Column("acknowledged_by", UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("dispatch_recommendations")
    op.drop_index("ix_regulatory_reports_country", "regulatory_reports")
    op.drop_table("regulatory_reports")
