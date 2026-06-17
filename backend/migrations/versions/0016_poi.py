"""poi_locations + poi_status_reports — Feature 9

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "poi_locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("poi_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("is_operational", sa.Boolean(), server_default="true"),
        sa.Column("reports_up", sa.Integer(), server_default="0"),
        sa.Column("reports_down", sa.Integer(), server_default="0"),
        sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_poi_locations_poi_type", "poi_locations", ["poi_type"])
    op.create_index("ix_poi_locations_h3", "poi_locations", ["h3_index"])

    op.create_table(
        "poi_status_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("poi_id", UUID(as_uuid=True),
                  sa.ForeignKey("poi_locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_operational", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.String(280), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("poi_status_reports")
    op.drop_index("ix_poi_locations_h3", "poi_locations")
    op.drop_index("ix_poi_locations_poi_type", "poi_locations")
    op.drop_table("poi_locations")
