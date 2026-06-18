"""0026 gnn predictions cascade risk

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def _is_pg():
    return op.get_bind().dialect.name == "postgresql"


def _uuid_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import UUID
        return UUID(as_uuid=True)
    return sa.String(36)


def _jsonb_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import JSONB
        return JSONB()
    return sa.Text()


def upgrade() -> None:
    op.create_table(
        "gnn_predictions",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("transformer_id", _uuid_col(),
                  sa.ForeignKey("grid_transformers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("predicted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("cascade_risk", sa.Float(), nullable=True),
        sa.Column("affected_cells", _jsonb_col(), nullable=True),
        sa.Column("model_version", sa.String(20), server_default="gnn_v0", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.create_index("ix_gnn_predictions_h3_index", "gnn_predictions", ["h3_index"])
    op.create_index("ix_gnn_predictions_predicted_at", "gnn_predictions", ["predicted_at"])


def downgrade() -> None:
    op.drop_table("gnn_predictions")
