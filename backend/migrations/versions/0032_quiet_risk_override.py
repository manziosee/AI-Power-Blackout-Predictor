"""0032 add quiet_risk_override to alert_subscriptions

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alert_subscriptions") as batch_op:
        batch_op.add_column(
            sa.Column("quiet_risk_override", sa.String(20), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("alert_subscriptions") as batch_op:
        batch_op.drop_column("quiet_risk_override")
