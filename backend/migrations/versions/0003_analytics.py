"""analytics — duration prediction columns + accuracy metrics table + cell stats

Revision ID: 0003
Revises: 0001
Create Date: 2026-05-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Duration prediction columns on predictions ────────────────────────────
    op.add_column("predictions", sa.Column("predicted_duration_min", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("predicted_duration_max", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("predicted_duration_median", sa.Integer(), nullable=True))

    # ── prediction_accuracy — per-cell monthly accuracy metrics ───────────────
    op.create_table(
        "prediction_accuracy",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_predictions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("true_positives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("false_positives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("true_negatives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("false_negatives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_accuracy_h3_period", "prediction_accuracy", ["h3_index", "period_start"])

    # ── neighborhood_stats — materialised ranking data ────────────────────────
    op.create_table(
        "neighborhood_stats",
        sa.Column("h3_index", sa.String(15), primary_key=True),
        sa.Column("country_code", sa.String(5), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("outages_7d", sa.Integer(), server_default="0"),
        sa.Column("outages_30d", sa.Integer(), server_default="0"),
        sa.Column("outages_90d", sa.Integer(), server_default="0"),
        sa.Column("avg_duration_minutes", sa.Float(), nullable=True),
        sa.Column("avg_probability_7d", sa.Float(), nullable=True),
        sa.Column("rank_country", sa.Integer(), nullable=True),
        sa.Column("rank_city", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_stats_country", "neighborhood_stats", ["country_code", "outages_30d"])
    op.create_index("idx_stats_city", "neighborhood_stats", ["city", "outages_30d"])


def downgrade() -> None:
    op.drop_table("neighborhood_stats")
    op.drop_table("prediction_accuracy")
    op.drop_column("predictions", "predicted_duration_median")
    op.drop_column("predictions", "predicted_duration_max")
    op.drop_column("predictions", "predicted_duration_min")
