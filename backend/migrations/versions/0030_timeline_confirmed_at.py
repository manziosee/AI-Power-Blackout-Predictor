"""0030 add confirmed_at to outage_reports for timeline feature

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("outage_reports") as batch_op:
        batch_op.add_column(
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("outage_reports") as batch_op:
        batch_op.drop_column("confirmed_at")
