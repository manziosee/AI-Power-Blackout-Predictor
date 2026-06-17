"""resilience_scores — Feature 4

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resilience_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("h3_index", sa.String(15), nullable=False, unique=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("outage_frequency_score", sa.Float(), nullable=True),
        sa.Column("avg_duration_score", sa.Float(), nullable=True),
        sa.Column("prediction_accuracy_score", sa.Float(), nullable=True),
        sa.Column("report_participation_score", sa.Float(), nullable=True),
        sa.Column("outages_30d", sa.Integer(), server_default="0"),
        sa.Column("avg_duration_minutes", sa.Float(), nullable=True),
        sa.Column("grade", sa.String(2), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("resilience_scores")
