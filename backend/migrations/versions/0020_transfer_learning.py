"""region_similarities — Feature 13

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "region_similarities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_region", sa.String(100), nullable=False),
        sa.Column("target_region", sa.String(100), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("basis", sa.String(50), server_default="climate"),
        sa.Column("climate_score", sa.Float(), nullable=True),
        sa.Column("infrastructure_score", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source_region", "target_region", name="uq_region_similarity"),
    )
    op.create_index("ix_region_similarities_source", "region_similarities", ["source_region"])
    op.create_index("ix_region_similarities_target", "region_similarities", ["target_region"])


def downgrade() -> None:
    op.drop_index("ix_region_similarities_target", "region_similarities")
    op.drop_index("ix_region_similarities_source", "region_similarities")
    op.drop_table("region_similarities")
