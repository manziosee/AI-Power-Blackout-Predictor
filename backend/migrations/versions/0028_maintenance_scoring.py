"""0028 maintenance scoring columns on grid_transformers

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("grid_transformers") as batch_op:
        batch_op.add_column(sa.Column("maintenance_risk_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("failure_count_90d", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("last_scored_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("grid_transformers") as batch_op:
        batch_op.drop_column("maintenance_risk_score")
        batch_op.drop_column("failure_count_90d")
        batch_op.drop_column("last_scored_at")
