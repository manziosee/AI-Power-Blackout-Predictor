"""0029 trust score on user_points weighted verification on outage_reports

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_points") as batch_op:
        batch_op.add_column(
            sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.5")
        )

    with op.batch_alter_table("outage_reports") as batch_op:
        batch_op.add_column(
            sa.Column("weighted_verification_score", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("outage_reports") as batch_op:
        batch_op.drop_column("weighted_verification_score")

    with op.batch_alter_table("user_points") as batch_op:
        batch_op.drop_column("trust_score")
