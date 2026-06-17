"""grid_transformers + transformer_cell_coverage — Feature 11

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grid_transformers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("transformer_type", sa.String(30), server_default="distribution"),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("h3_index", sa.String(15), nullable=True),
        sa.Column("capacity_kva", sa.Float(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("utility_id", UUID(as_uuid=True),
                  sa.ForeignKey("utility_companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("last_maintenance_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_grid_transformers_h3", "grid_transformers", ["h3_index"])

    op.create_table(
        "transformer_cell_coverage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("transformer_id", UUID(as_uuid=True),
                  sa.ForeignKey("grid_transformers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="true"),
        sa.UniqueConstraint("transformer_id", "h3_index", name="uq_transformer_cell"),
    )
    op.create_index("ix_transformer_cell_h3", "transformer_cell_coverage", ["h3_index"])


def downgrade() -> None:
    op.drop_index("ix_transformer_cell_h3", "transformer_cell_coverage")
    op.drop_table("transformer_cell_coverage")
    op.drop_index("ix_grid_transformers_h3", "grid_transformers")
    op.drop_table("grid_transformers")
